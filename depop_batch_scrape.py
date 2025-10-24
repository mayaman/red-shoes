#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Batch-scrape Depop product pages:
- Uses Playwright to avoid 403s
- Extracts only the large displayed gallery images in the desktop container (1280x1280)
- Saves each product into OUT_DIR/<product-folder>/images/
- Writes a master OUT_DIR/products.json mapping products to images with clean relative paths

Usage examples:
  pip3 install playwright beautifulsoup4 tqdm
  python3 -m playwright install chromium

  python3 depop_batch_scrape.py --out ./depop_out "https://www.depop.com/products/.../"

  python3 depop_batch_scrape.py --out ./depop_out --urls-file urls.txt
  # urls.txt can be plain text (one URL per line) or a JSON array of URLs
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from tqdm import tqdm
from playwright.sync_api import sync_playwright


# ---------------------------
# Utilities
# ---------------------------

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

def slugify(text: str, keep_ext: bool = False):
    """
    Make a filesystem-safe slug.
    """
    if not text:
        return "item"
    text = text.strip().lower()
    # replace separators
    text = re.sub(r"[^\w\-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if not text:
        text = "item"
    if not keep_ext:
        text = text.rstrip(".")
    return text[:100]  # keep short-ish


# ---------------------------
# Parsing helpers
# ---------------------------

def parse_json_ld(soup: BeautifulSoup):
    """
    Read JSON-LD for product info (title/description/price/currency).
    We IGNORE its image array since we only want the displayed big images.
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

def extract_exact_large_gallery_images(soup: BeautifulSoup, base_url: str):
    """
    Strictly collect ONLY the large displayed gallery images:
    - inside div[data-testid="desktop"]
    - <img> with width="1280" and height="1280"
    - gallery class pattern (if hashes change, we also try a broader fallback)
    - hosted on media-photos.depop.com
    - prefer img[src], fallback to custom CSS var --background-image
    """
    images = []
    gallery = soup.select_one('div[data-testid="desktop"]')
    if not gallery:
        return []

    # Try exact class combo first (from observed markup)
    exact_imgs = gallery.select(
        'img.styles_imageItem__UWJs6.styles_imageItemNonSquare__VJ0R6[width="1280"][height="1280"]'
    )

    # Fallback: class contains patterns + size attributes
    if not exact_imgs:
        exact_imgs = gallery.select(
            'img[width="1280"][height="1280"][class*="styles_imageItem"][class*="styles_imageItemNonSquare"]'
        )

    for img in exact_imgs:
        src = img.get("src")
        style = img.get("style") or ""
        m = re.search(r"--background-image:\s*([^;]+)", style)
        bg = (m.group(1).strip() if m else None)

        candidate = src or bg
        if not candidate:
            continue
        candidate = absolutize(candidate, base_url)

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

    # Only the big gallery images:
    info["images"] = extract_exact_large_gallery_images(soup, base_url)
    return info


# ---------------------------
# Downloading & batch logic
# ---------------------------

def download_images(image_urls, product_folder: Path, request_ctx):
    """
    Download images to product_folder / 'images'.
    Returns list of dicts: {"filename", "url", "path"} where "path" is relative to OUT_DIR.
    """
    images_dir = product_folder / "images"
    ensure_dir(images_dir)
    saved = []

    for i, url in enumerate(tqdm(image_urls, desc=f"Downloading images -> {product_folder.name}", leave=False)):
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1] or ".jpg"
        # Normalize extensions like ".jpg?…" -> ".jpg"
        ext = ext.split("?")[0] or ".jpg"
        fname = f"image_{i+1:02d}{ext}"
        fpath = images_dir / fname

        try:
            resp = request_ctx.get(url, timeout=30000)
            if not resp.ok:
                print(f"[warn] {url} -> HTTP {resp.status}")
                continue
            with open(fpath, "wb") as f:
                f.write(resp.body())

            # path relative to the OUT_DIR (two dirs up from images_dir)
            # We'll compute relative later in batch runner (we know OUT_DIR then).
            saved.append({"filename": fname, "url": url, "abs_path": str(fpath)})
        except Exception as e:
            print(f"[warn] Failed to download {url}: {e}")
        time.sleep(0.03)

    return saved

def pick_product_folder_name(url: str, title: str | None):
    """
    Make a stable folder name per product. Prefer last path segment from URL; fall back to title; else a hash-ish slug.
    """
    # Try URL tail like /products/<slug>/
    try:
        path_segs = [seg for seg in urlparse(url).path.split("/") if seg]
        tail = path_segs[-1] if path_segs else None
    except Exception:
        tail = None

    candidates = []
    if tail:
        candidates.append(tail)
    if title:
        candidates.append(title)
    # fallback
    candidates.append(re.sub(r"[^a-z0-9]+", "-", (url or "").lower()).strip("-"))

    base = slugify(next((c for c in candidates if c), "item"))
    return base or "item"

def read_urls_from_file(p: Path):
    """
    Supports:
      - TXT: one URL per line
      - JSON: array of strings (URLs)
    """
    text = p.read_text(encoding="utf-8").strip()
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of URLs.")
        urls = [str(u).strip() for u in data if str(u).strip()]
        return urls
    else:
        # treat as plain text
        urls = [line.strip() for line in text.splitlines() if line.strip()]
        return urls

def batch_scrape(urls, out_dir: Path, wait_ms: int = 2000):
    ensure_dir(out_dir)
    results = []

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

        for url in tqdm(urls, desc="Scraping products"):
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                print(f"[warn] Failed to navigate: {url} ({e})")
                continue

            page.wait_for_timeout(wait_ms)
            try:
                page.wait_for_selector('div[data-testid="desktop"] img', timeout=5000)
            except Exception:
                pass

            html = page.content()
            info = extract_page_data(html, url)

            # Choose product folder name and ensure uniqueness in OUT_DIR
            base_folder_name = pick_product_folder_name(url, info.get("title"))
            product_folder = out_dir / base_folder_name
            # if exists, add -2, -3, etc.
            suffix = 2
            while product_folder.exists():
                product_folder = out_dir / f"{base_folder_name}-{suffix}"
                suffix += 1
            ensure_dir(product_folder)

            # Download images
            saved_images = download_images(info.get("images", []), product_folder, context.request)

            # Convert abs paths to paths relative to OUT_DIR for portability
            rel_images = []
            for im in saved_images:
                rel_path = os.path.relpath(im["abs_path"], start=out_dir)
                rel_images.append({
                    "filename": im["filename"],
                    "url": im["url"],
                    "path": rel_path
                })

            product_entry = {
                "id": product_folder.name,
                "source_url": url,
                "title": info.get("title"),
                "description": info.get("description"),
                "price": info.get("price"),
                "currency": info.get("currency"),
                "folder": product_folder.name,
                "images": rel_images
            }
            results.append(product_entry)

        browser.close()

    # Write master JSON
    manifest = {
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "products": results
    }
    json_path = out_dir / "products.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return {"json_path": str(json_path), "product_count": len(results)}


# ---------------------------
# CLI
# ---------------------------

def main():
    ap = argparse.ArgumentParser(description="Batch scrape Depop products; only large displayed gallery images.")
    ap.add_argument("urls", nargs="*", help="Product URLs (space-separated). Optional if --urls-file is given.")
    ap.add_argument("--urls-file", help="Path to a file containing URLs (txt: one per line; json: array).")
    ap.add_argument("--out", default="./depop_out", help="Output directory (default: ./depop_out)")
    ap.add_argument("--wait-ms", type=int, default=2000, help="Extra wait after load to let images render (ms)")
    args = ap.parse_args()

    url_list = []
    if args.urls_file:
        p = Path(args.urls_file)
        if not p.exists():
            print(f"[error] URLs file not found: {p}")
            sys.exit(1)
        url_list.extend(read_urls_from_file(p))
    if args.urls:
        url_list.extend(args.urls)

    # dedupe while preserving order
    seen = set()
    final_urls = []
    for u in url_list:
        if u not in seen:
            seen.add(u)
            final_urls.append(u)

    if not final_urls:
        print("[error] No URLs provided.")
        sys.exit(2)

    out_dir = Path(args.out)
    ensure_dir(out_dir)

    result = batch_scrape(final_urls, out_dir, wait_ms=args.wait_ms)
    print(f"\nDone.\n- products.json: {result['json_path']}\n- Products scraped: {result['product_count']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
