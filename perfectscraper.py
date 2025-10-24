#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from tqdm import tqdm
from playwright.sync_api import sync_playwright

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def unique(seq):
    seen = set()
    out = []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out

def absolutize(url: str, base: str):
    try:
        return urljoin(base, url)
    except Exception:
        return url

def parse_json_ld(soup: BeautifulSoup):
    # Only for title/description/price – we IGNORE images from JSON-LD.
    out = {"title": None, "description": None, "price": None, "currency": None}
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type") or item.get("type")
            is_product = "Product" in t if isinstance(t, list) else (t == "Product")
            if is_product:
                out["title"] = out["title"] or item.get("name")
                out["description"] = out["description"] or item.get("description")
                offers = item.get("offers")
                if isinstance(offers, dict):
                    out["price"] = out["price"] or offers.get("price")
                    out["currency"] = out["currency"] or offers.get("priceCurrency")
    return out

def extract_exact_large_gallery_images(soup: BeautifulSoup, base_url: str):
    """
    Strictly collect ONLY the large displayed gallery images the user wants:
    - Must be inside the desktop gallery: div[data-testid="desktop"]
    - Must be <img> with width="1280" and height="1280"
    - Must match Depop gallery classes (like styles_imageItem__... styles_imageItemNonSquare__...)
    - Must be hosted on media-photos.depop.com
    - Prefer <img src>; fallback to --background-image in style
    """
    images = []
    gallery = soup.select_one('div[data-testid="desktop"]')
    if not gallery:
        return []

    # Exact class names (from your snippet). If Depop’s hashes change, broaden the selector below.
    exact_imgs = gallery.select(
        'img.styles_imageItem__UWJs6.styles_imageItemNonSquare__VJ0R6[width="1280"][height="1280"]'
    )

    # If classes ever change, uncomment this broader fallback:
    # if not exact_imgs:
    #     exact_imgs = gallery.select('img[width="1280"][height="1280"][class*="styles_imageItem"][class*="styles_imageItemNonSquare"]')

    for img in exact_imgs:
        # Prefer src
        src = img.get("src")
        # Fallback to CSS var
        style = img.get("style") or ""
        m = re.search(r"--background-image:\s*([^;]+)", style)
        bg = (m.group(1).strip() if m else None)

        candidate = src or bg
        if not candidate:
            continue

        candidate = absolutize(candidate, base_url)

        # Keep only Depop media host + real image extensions
        parsed = urlparse(candidate)
        path = parsed.path.lower()
        if ("media-photos.depop.com" in parsed.netloc and
            path.endswith((".jpg", ".jpeg", ".png", ".webp"))):
            images.append(candidate)

    return unique(images)

def extract_page_data(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    info = parse_json_ld(soup)

    # Fallback title/description
    if not info.get("title") and soup.title and soup.title.string:
        info["title"] = soup.title.string.strip()

    if not info.get("description"):
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            info["description"] = meta_desc["content"].strip()
    if not info.get("description"):
        desc_candidates = soup.select('[data-testid*="description"], [class*="Description"], [class*="description"]')
        for c in desc_candidates:
            txt = c.get_text(" ", strip=True)
            if txt and len(txt) > 20:
                info["description"] = txt
                break

    # >>> ONLY the exact large displayed images
    info["images"] = extract_exact_large_gallery_images(soup, base_url)
    return info

def download_images(image_urls, out_dir: Path, page_request=None):
    saved = []
    ensure_dir(out_dir)
    for i, url in enumerate(tqdm(image_urls, desc="Downloading images")):
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1] or ".jpg"
        fname = f"image_{i+1:02d}{ext.split('?')[0]}"
        fpath = out_dir / fname
        try:
            if page_request is None:
                raise RuntimeError("No request context available for download")
            resp = page_request.get(url, timeout=30000)
            if not resp.ok:
                print(f"[warn] {url} -> HTTP {resp.status}")
                continue
            with open(fpath, "wb") as f:
                f.write(resp.body())
            saved.append({"filename": fname, "url": url})
        except Exception as e:
            print(f"[warn] Failed to download {url}: {e}")
        time.sleep(0.05)
    return saved

def scrape_depop_product(url: str, out_dir: Path, wait_ms: int = 2000):
    ensure_dir(out_dir)
    images_dir = out_dir / "images"
    ensure_dir(images_dir)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/119.0.0.0 Safari/537.36"),
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(wait_ms)

        # Ensure the gallery rendered (don’t fail hard if not)
        try:
            page.wait_for_selector('div[data-testid="desktop"] img', timeout=5000)
        except Exception:
            pass

        html = page.content()
        info = extract_page_data(html, url)
        saved_images = download_images(info.get("images", []), images_dir, page_request=context.request)

        data = {
            "source_url": url,
            "title": info.get("title"),
            "description": info.get("description"),
            "price": info.get("price"),
            "currency": info.get("currency"),
            "images": saved_images,
        }

        json_path = out_dir / "data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        browser.close()

    return {"json_path": str(json_path), "image_count": len(saved_images)}

def main():
    ap = argparse.ArgumentParser(description="Scrape a Depop product page (ONLY large displayed gallery images + description) to JSON.")
    ap.add_argument("url", help="Depop product URL")
    ap.add_argument("--out", default="./depop_item", help="Output directory (default: ./depop_item)")
    ap.add_argument("--wait-ms", type=int, default=2000, help="Extra wait after load to let images render (ms)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    result = scrape_depop_product(args.url, out_dir, wait_ms=args.wait_ms)
    print(f"\nDone.\n- JSON: {result['json_path']}\n- Images saved: {result['image_count']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
