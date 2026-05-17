import os
import requests
import logging
from pathlib import Path

logger = logging.getLogger("filmden.pipeline.fetch_visuals")

TMP_DIR = Path("filmden/tmp_assets")

import random

def download_movie_visuals(movie_name: str) -> list[str]:
    """
    Searches TMDB for the movie and downloads its poster + up to 4 random screenshots (backdrops).
    Returns a list of file paths of the downloaded images.
    """
    tmdb_key = os.getenv("TMDB_API_KEY")
    if not tmdb_key:
        logger.error("TMDB_API_KEY is not set.")
        return []

    # 1. Search for the movie
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": tmdb_key,
        "query": movie_name
    }
    
    downloaded_paths = []
    
    try:
        resp = requests.get(search_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("results"):
            logger.warning("No visual found on TMDB for movie: %s", movie_name)
            return []
            
        first_movie = data["results"][0]
        movie_id = first_movie["id"]
        
        # 2. Fetch all images for this movie
        images_url = f"https://api.themoviedb.org/3/movie/{movie_id}/images"
        # We don't specify language to get all backdrops
        img_resp = requests.get(images_url, params={"api_key": tmdb_key}, timeout=10)
        img_resp.raise_for_status()
        img_data = img_resp.json()
        
        # 3. Select images to download
        images_to_download = []
        
        # Always try to get the primary poster first
        if first_movie.get("poster_path"):
            images_to_download.append(first_movie["poster_path"])
            
        # Get up to 4 random backdrops (screenshots)
        backdrops = img_data.get("backdrops", [])
        if backdrops:
            # Shuffle and pick up to 4
            random.shuffle(backdrops)
            selected_backdrops = backdrops[:4]
            for bd in selected_backdrops:
                if bd.get("file_path"):
                    images_to_download.append(bd["file_path"])
                    
        if not images_to_download:
            logger.warning("Movie found on TMDB, but no images available: %s", movie_name)
            return []
            
        # 4. Download the images
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = "".join([c if c.isalnum() else "_" for c in movie_name])
        
        for idx, img_path in enumerate(images_to_download):
            image_url = f"https://image.tmdb.org/t/p/original{img_path}"
            
            # Label the first one as poster, rest as screenshot
            suffix = "poster" if idx == 0 and first_movie.get("poster_path") == img_path else f"screenshot_{idx}"
            save_path = TMP_DIR / f"{safe_name}_{suffix}.jpg"
            
            try:
                dl_resp = requests.get(image_url, timeout=30)
                dl_resp.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(dl_resp.content)
                downloaded_paths.append(str(save_path))
                logger.info("Successfully downloaded %s: %s", suffix, save_path)
            except Exception as dl_err:
                logger.error("Failed to download image %s: %s", image_url, dl_err)
                
        return downloaded_paths

    except Exception as e:
        logger.error("Failed to fetch visuals for %s: %s", movie_name, e)
        return []
