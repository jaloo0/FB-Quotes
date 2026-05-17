import os
import logging
import requests

logger = logging.getLogger("filmden.pipeline.trakt_movies")

TRAKT_BASE = "https://api.trakt.tv"
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"


def _trakt_headers() -> dict:
    client_id = os.getenv("TRAKT_CLIENT_ID")
    if not client_id:
        raise RuntimeError("TRAKT_CLIENT_ID is not set.")
    return {
        "Content-Type": "application/json",
        "trakt-api-client-id": client_id,
        "trakt-api-version": "2",
    }


def _tmdb_headers() -> dict:
    token = os.getenv("TMDB_API_READ_TOKEN")
    if not token:
        raise RuntimeError("TMDB_API_READ_TOKEN is not set.")
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }


def fetch_trakt_movies(endpoint: str = "trending", limit: int = 30) -> list[dict]:
    """
    Fetches movies from Trakt (trending, popular, etc.).
    Returns a list of dicts with 'title' and 'tmdb_id'.
    """
    url = f"{TRAKT_BASE}/movies/{endpoint}?limit={limit}"
    resp = requests.get(url, headers=_trakt_headers(), timeout=15)
    resp.raise_for_status()

    movies = []
    for item in resp.json():
        # trending wraps in {'watchers': N, 'movie': {...}}, popular is a flat list
        movie = item.get("movie", item)
        tmdb_id = movie.get("ids", {}).get("tmdb")
        title = movie.get("title")
        year = movie.get("year")
        if tmdb_id and title:
            movies.append({"title": title, "year": year, "tmdb_id": tmdb_id})

    logger.info("Fetched %d movies from Trakt /%s", len(movies), endpoint)
    return movies


def enrich_with_tmdb(tmdb_id: int) -> dict:
    """
    Fetches movie details + images from TMDB using its numeric ID.
    Returns a dict with 'overview', 'poster_url', 'backdrop_url', 'tagline', 'rating'.
    """
    tmdb_key = os.getenv("TMDB_API_KEY")
    details: dict = {}

    try:
        # --- Movie details ---
        detail_url = f"{TMDB_BASE}/movie/{tmdb_id}"
        params = {"api_key": tmdb_key, "language": "en-US"}
        resp = requests.get(detail_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        poster_path = data.get("poster_path")
        backdrop_path = data.get("backdrop_path")

        details = {
            "overview": data.get("overview", ""),
            "tagline": data.get("tagline", ""),
            "rating": data.get("vote_average"),
            "poster_url": f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None,
            "backdrop_url": f"{TMDB_IMAGE_BASE}{backdrop_path}" if backdrop_path else None,
        }

        # --- Additional backdrop images ---
        images_url = f"{TMDB_BASE}/movie/{tmdb_id}/images"
        img_resp = requests.get(images_url, params={"api_key": tmdb_key}, timeout=10)
        img_resp.raise_for_status()
        img_data = img_resp.json()

        backdrops = img_data.get("backdrops", [])[:3]  # up to 3 extra backdrops
        details["extra_backdrops"] = [
            f"{TMDB_IMAGE_BASE}{b['file_path']}"
            for b in backdrops
            if b.get("file_path")
        ]

    except Exception as e:
        logger.error("Failed to enrich TMDB data for id=%s: %s", tmdb_id, e)

    return details


def get_fresh_movie(skip_tmdb_ids: set) -> dict | None:
    """
    Fetches trending then popular movies from Trakt, skips already-posted ones,
    enriches the first fresh pick with TMDB data, and returns it.
    Returns None if everything has already been posted.
    """
    candidates = fetch_trakt_movies("trending", limit=30)
    # Fallback: also pull popular in case all trending are exhausted
    candidates += fetch_trakt_movies("popular", limit=30)

    seen = set()
    for movie in candidates:
        tmdb_id = movie["tmdb_id"]
        if tmdb_id in seen or tmdb_id in skip_tmdb_ids:
            continue
        seen.add(tmdb_id)

        logger.info("Selected fresh movie: %s (tmdb_id=%s)", movie["title"], tmdb_id)
        enriched = enrich_with_tmdb(tmdb_id)
        return {**movie, **enriched}

    logger.warning("No fresh movies found — all candidates already posted.")
    return None
