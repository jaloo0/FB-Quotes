import os
import logging
import requests
from pathlib import Path

logger = logging.getLogger("filmden.pipeline.fetch_visuals")

TMP_DIR = Path("filmden/tmp_assets")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


def download_visuals_by_urls(movie_title: str, urls: list[str]) -> list[str]:
    """
    Downloads images from a list of TMDB image URLs.
    Returns a list of local file paths of downloaded images.
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join([c if c.isalnum() else "_" for c in movie_title])
    downloaded = []

    for idx, url in enumerate(urls):
        if not url:
            continue
        label = "poster" if idx == 0 else f"backdrop_{idx}"
        save_path = TMP_DIR / f"{safe_name}_{label}.jpg"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            save_path.write_bytes(resp.content)
            downloaded.append(str(save_path))
            logger.info("Downloaded %s -> %s", label, save_path)
        except Exception as e:
            logger.error("Failed to download %s: %s", url, e)

    return downloaded


def download_movie_visuals_by_id(tmdb_id: int, movie_title: str) -> list[str]:
    """
    Given a TMDB movie ID, downloads the poster and up to 3 backdrop images.
    Returns a list of local file paths.
    """
    tmdb_key = os.getenv("TMDB_API_KEY")
    if not tmdb_key:
        logger.error("TMDB_API_KEY is not set.")
        return []

    try:
        # Fetch movie details for the primary poster
        detail_resp = requests.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={"api_key": tmdb_key, "language": "en-US"},
            timeout=10,
        )
        detail_resp.raise_for_status()
        data = detail_resp.json()

        urls = []
        if data.get("poster_path"):
            urls.append(f"{TMDB_IMAGE_BASE}{data['poster_path']}")
        if data.get("backdrop_path"):
            urls.append(f"{TMDB_IMAGE_BASE}{data['backdrop_path']}")

        # Fetch additional backdrops
        img_resp = requests.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}/images",
            params={"api_key": tmdb_key},
            timeout=10,
        )
        img_resp.raise_for_status()
        for bd in img_resp.json().get("backdrops", [])[:2]:
            fp = bd.get("file_path")
            if fp:
                urls.append(f"{TMDB_IMAGE_BASE}{fp}")

        return download_visuals_by_urls(movie_title, urls)

    except Exception as e:
        logger.error("Failed to fetch visuals for tmdb_id=%s: %s", tmdb_id, e)
        return []
