#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scrape a single Depop product page:
- Loads the page with Playwright (avoids 403 from plain requests)
- Extracts product title, description, price, currency (if available)
- **Only** collects the large gallery images inside the desktop gallery container
- Downloads images to disk
- Writes a data.json file with the structured result

Usage:
  pip3 install playwright beautifulsoup4 tqdm
  python3 -m playwright install chromium
  python3 depop_scrape_product.py "https://www.depop.com/products/..." --out ./depop_item
"""

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


def pick_largest_from_srcset(srcset: str):
    """
    Given a srcset string, return the URL with the largest width descriptor.
    """
    if not srcset:
        return None
    candidates = []
    for part in srcset.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"([^\s]+)\s+(\d+)w", part)
        if m:
            url, w = m.group(1), int(m.group(2))
            candidates.append((w, url))
        else:
            # handle single url without descriptor
            candidates.append((0, part.split()[0]))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def absolutize(url: str, base: str):
    try:
        return urljoin(base, url)
    except Exception:
        return url


def parse_json_ld(soup: BeautifulSoup):
    """
    Look for Product JSON-LD blocks to get images/description/price.
    (We still read these for title/description/price, but we IGNORE json-ld images now.)
    """
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


def extract_large_gallery_images(soup: BeautifulSoup, base_url: str):
    """
    Only collect the large product images from the desktop gallery container.

    We look for:
      - div[data-testid="desktop"] as the parent gallery
      - descendant <img> tags (with src/srcset)
      - the custom CSS var style="--background-image: https://...P0.jpg" as fallback

    We prefer:
      1) largest srcset URL
      2) src
      3) --background-image value

    We also bias for big images by checking width/height attributes (>=1000).
    """
    images = []
    gallery = soup.select_one('div[data-testid="desktop"]')
    if not gallery:
        return []

    # All <img> inside gallery
    for img in gallery.find_all("img"):
        # Bias to large assets (often 1280 x 1280)
        try:
            w = int(img.get("width") or 0)
            h = int(img.get("height") or 0)
        except ValueError:
            w, h = 0, 0

        # If width/height are present, prefer large ones; if not present, accept anyway (some browsers omit)
        is_large = (w >= 1000 and h >= 1000) or (w == 0 and h == 0)

        if is_large:
            srcset = img.get("srcset")
            src = pick_largest_from_srcset(srcset) or img.get("src")
            if src:
                images.append(src)

            # Fallback: custom CSS var used by Depop
            style = img.get("style") or ""
            m = re.search(r"--background-image:\s*([^;]+)", style)
            if m:
                images.append(m.group(1).strip())

    # Also check gallery descendant divs for the same CSS var (some builds place it on the wrapper)
    for tag in gallery.find_all(True, attrs={"style": True}):
        style = tag.get("style") or ""
        m_all = re.findall(r"--background-image:\s*([^;]+)", style)
        for u in m_all:
            images.append(u.strip())

    # Absolutize and dedupe
    images = [absolutize(u, base_url) for u in images if u]
    images = unique(images)

    # Keep only actual image file types and prefer Depop media host
    def is_gallery_asset(u: str):
        parsed = urlparse(u)
        path = parsed.path.lower()
        ok_ext = path.endswith((".jpg", ".jpeg", ".png", ".webp"))
        host_pref = "media-photos.depop.com" in parsed.netloc
        return ok_ext and host_pref

    images = [u for u in images if is_gallery_asset(u)]
    return images


def extract_page_data(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")

    # JSON-LD for title/description/price/currency (but not images)
    info = parse_json_ld(soup)

    # Title fallback
    if not info.get("title"):
        if soup.title and soup.title.string:
            info["title"] = soup.title.string.strip()

    # Description fallbacks
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

    # >>> Only collect large gallery images from the desktop container <<<
    images = extract_large_gallery_images(soup, base_url)
    info["images"] = images

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
            content = resp.body()
            with open(fpath, "wb") as f:
                f.write(content)
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
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = context.new_page()

        # Navigate and wait for the network to settle
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(wait_ms)

        # Best-effort: ensure the desktop gallery has rendered at least once
        try:
            page.wait_for_selector('div[data-testid="desktop"] img', timeout=5000)
        except Exception:
            # proceed anyway; extract function will return empty list if not found
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
    ap = argparse.ArgumentParser(description="Scrape a Depop product page (gallery images + description) to JSON.")
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
