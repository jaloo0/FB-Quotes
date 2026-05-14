"""
image_fetcher.py
----------------
Hits the Pexels API, downloads a high-quality image, and returns
the local path plus the tags returned by Pexels.
"""

import os
import random
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

PEXELS_BASE = "https://api.pexels.com/v1/search"
PEXELS_VIDEO_BASE = "https://api.pexels.com/videos/search"   # not used, future
OUTPUT_DIR = Path("tmp_assets")


def _headers() -> dict:
    key = os.environ["PEXELS_API_KEY"]
    return {"Authorization": key}


def search_image(query: str, per_page: int = 15) -> list[dict]:
    """
    Search Pexels and return a list of photo result dicts.
    Each dict has keys: id, url, photographer, src (urls), alt (tags-ish).
    """
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "portrait",  # better for FB feed
        "size": "large",
    }
    resp = requests.get(PEXELS_BASE, headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("photos", [])


def extract_tags(photo: dict) -> list[str]:
    """
    Pexels doesn't expose explicit tags in free tier, so we derive pseudo-tags
    from the `alt` field and the `query` string embedded in `url`.
    Returns a lowercase list of words useful for vibe matching.
    """
    alt_text = photo.get("alt", "")
    # Split alt text into words, strip punctuation
    words = [w.strip(",.!?-").lower() for w in alt_text.split() if len(w) > 2]
    return list(set(words))


def download_photo(photo: dict) -> Path:
    """Download the 'large2x' (≈2000 px) version and save to tmp_assets/."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    url = photo["src"]["large2x"]
    photo_id = photo["id"]
    dest = OUTPUT_DIR / f"photo_{photo_id}.jpg"
    if dest.exists():
        logger.info("Photo already cached: %s", dest)
        return dest
    resp = requests.get(url, timeout=30, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
    logger.info("Downloaded %s -> %s", url, dest)
    return dest


def fetch_image_for_vibe(
    query: str,
    vibe: str,
    tags_match_fn,          # callable(vibe, tags) -> bool
    max_candidates: int = 15,
) -> tuple[Path, list[str]] | None:
    """
    Search Pexels with `query`, filter by vibe tag-match, download best match.
    Returns (local_path, tags) or None if nothing suitable found.
    """
    photos = search_image(query, per_page=max_candidates)
    if not photos:
        logger.warning("No photos returned for query: %s", query)
        return None

    # Score and filter by tag match
    matched = []
    for photo in photos:
        tags = extract_tags(photo)
        if tags_match_fn(vibe, tags):
            matched.append((photo, tags))

    if not matched:
        logger.info("No tag-matched photos – falling back to random pick.")
        photo = random.choice(photos)
        tags = extract_tags(photo)
    else:
        photo, tags = random.choice(matched)

    local_path = download_photo(photo)
    return local_path, tags
