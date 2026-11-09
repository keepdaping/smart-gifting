"""
Download free, licensed photos for every store menu item.

Run this on your own computer (it needs internet access):

    # Pexels (recommended: 200 requests/hour, free key at https://www.pexels.com/api/)
    set PEXELS_API_KEY=your-key          # macOS/Linux: export PEXELS_API_KEY=your-key
    python fetch_images.py

    # or Unsplash (demo keys allow 50 requests/hour, key at https://unsplash.com/developers)
    set UNSPLASH_ACCESS_KEY=your-key
    python fetch_images.py --source unsplash

Options:
    --store java-house    only one store (use the slug from store_menus.py)
    --force               re-download images that already exist
    --dry-run             show what would be downloaded

Photos are saved as static/img/<store-slug>/<image>.jpg (800x600 JPEG).
Photographer credits are written to static/img/credits.json and shown on /credits.
Existing files are skipped, so you can stop and re-run at any time.
KFC is skipped because it uses photos of the real KFC Uganda menu.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from store_menus import IMAGE_QUERIES, STORE_MENUS

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "static" / "img"
CREDITS_FILE = IMG_DIR / "credits.json"
USER_AGENT = "SmartGiftingStudentProject/1.0"


def http_get(url, headers=None, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers


def search_pexels(query, key):
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "per_page": 1, "orientation": "landscape"}
    )
    body, headers = http_get(url, {"Authorization": key})
    photos = json.loads(body).get("photos", [])
    if not photos:
        return None, headers.get("X-Ratelimit-Remaining")
    photo = photos[0]
    return {
        "download": photo["src"]["landscape"],  # 1200x627 crop served by Pexels
        "photographer": photo["photographer"],
        "photographer_url": photo["photographer_url"],
        "page": photo["url"],
        "source": "Pexels",
    }, headers.get("X-Ratelimit-Remaining")


def search_unsplash(query, key):
    url = "https://api.unsplash.com/search/photos?" + urllib.parse.urlencode(
        {"query": query, "per_page": 1, "orientation": "landscape", "content_filter": "high"}
    )
    auth = {"Authorization": f"Client-ID {key}", "Accept-Version": "v1"}
    body, headers = http_get(url, auth)
    results = json.loads(body).get("results", [])
    if not results:
        return None, headers.get("X-Ratelimit-Remaining")
    photo = results[0]
    # Unsplash's API guidelines ask apps to register each download.
    try:
        http_get(photo["links"]["download_location"], auth)
    except urllib.error.URLError:
        pass
    utm = "?utm_source=smart_gifting&utm_medium=referral"
    return {
        "download": photo["urls"]["raw"] + "&w=800&h=600&fit=crop&q=75&fm=jpg",
        "photographer": photo["user"]["name"],
        "photographer_url": photo["user"]["links"]["html"] + utm,
        "page": photo["links"]["html"] + utm,
        "source": "Unsplash",
    }, headers.get("X-Ratelimit-Remaining")


def save_resized(raw, destination):
    """Save as an 800x600 JPEG; uses Pillow when installed, otherwise saves as served."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        from io import BytesIO

        from PIL import Image, ImageOps

        image = Image.open(BytesIO(raw)).convert("RGB")
        image = ImageOps.fit(image, (800, 600), Image.LANCZOS)
        image.save(destination, "JPEG", quality=80, optimize=True, progressive=True)
    except ImportError:
        destination.write_bytes(raw)


def jobs(only_store=None):
    for store_name, store in STORE_MENUS.items():
        slug = store["slug"]
        if only_store and only_store not in (slug, store_name):
            continue
        queries = IMAGE_QUERIES.get(slug, {})
        seen = set()
        for section, name, _variant, _desc, _price, _tags, image in store["items"]:
            if not image or image in seen:
                continue
            seen.add(image)
            yield store_name, slug, image, queries.get(image) or name


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=["pexels", "unsplash"], default=None)
    parser.add_argument("--store", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = args.source or ("unsplash" if os.environ.get("UNSPLASH_ACCESS_KEY") and not os.environ.get("PEXELS_API_KEY") else "pexels")
    key = os.environ.get("PEXELS_API_KEY" if source == "pexels" else "UNSPLASH_ACCESS_KEY")
    if not key and not args.dry_run:
        sys.exit(f"Set {'PEXELS_API_KEY' if source == 'pexels' else 'UNSPLASH_ACCESS_KEY'} first (see the top of this file).")
    search = search_pexels if source == "pexels" else search_unsplash

    credits = json.loads(CREDITS_FILE.read_text()) if CREDITS_FILE.is_file() else {}
    done = skipped = failed = 0
    for store_name, slug, image, query in jobs(args.store):
        relative = f"{slug}/{image}.jpg"
        destination = IMG_DIR / relative
        if destination.is_file() and not args.force:
            skipped += 1
            continue
        if args.dry_run:
            print(f"would fetch  {relative:45} <- '{query}'")
            continue
        try:
            photo, remaining = search(query, key)
            if not photo:
                print(f"no result    {relative} for '{query}' (edit IMAGE_QUERIES and re-run)")
                failed += 1
                continue
            raw, _ = http_get(photo.pop("download"), timeout=60)
            save_resized(raw, destination)
            credits[relative] = {"store": store_name, "query": query, **photo}
            CREDITS_FILE.write_text(json.dumps(credits, indent=2, sort_keys=True))
            done += 1
            print(f"saved        {relative:45} by {photo['photographer']} ({photo['source']})")
            if remaining is not None and int(remaining) <= 1:
                print("Rate limit reached. Wait an hour, then run the script again to continue.")
                break
            time.sleep(0.4)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                print("Rate limit reached. Wait an hour, then run the script again to continue.")
                break
            print(f"failed       {relative}: HTTP {exc.code}")
            failed += 1
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"failed       {relative}: {exc}")
            failed += 1

    print(f"\nDone. {done} downloaded, {skipped} already present, {failed} failed.")
    print("Check coverage with: flask --app app check-images")


if __name__ == "__main__":
    main()
