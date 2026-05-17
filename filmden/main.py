import os
import logging
from dotenv import load_dotenv
import sys

load_dotenv()

from filmden.db.trakt_schema import init_db, get_posted_ids, log_posted_movie
from filmden.pipeline.trakt_movies import get_fresh_movie
from filmden.pipeline.fetch_visuals import download_movie_visuals_by_id

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from pipeline.temp_uploader import upload_to_temp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] filmden: %(message)s",
)
logger = logging.getLogger("filmden")


def run():
    logger.info("━━━ Filmden Run Started ━━━")

    # 1. Bootstrap the database
    init_db()

    # 2. Get all already-posted movie IDs to avoid repeats
    posted_ids = get_posted_ids()
    logger.info("Already posted: %d movies", len(posted_ids))

    # 3. Fetch a fresh, not-yet-posted movie from Trakt + enrich via TMDB
    movie = get_fresh_movie(skip_tmdb_ids=posted_ids)

    if not movie:
        logger.error("No fresh movies available from Trakt. All candidates already posted.")
        logger.info("━━━ Filmden Run Complete (nothing to post) ━━━")
        return

    logger.info("🎬 Selected movie: %s (%s)", movie["title"], movie.get("year"))
    logger.info("Overview: %s", movie.get("overview", "N/A")[:200])
    logger.info("Rating: %s | Tagline: %s", movie.get("rating"), movie.get("tagline"))

    # 4. Download visuals (poster + backdrops) via TMDB ID
    image_paths = download_movie_visuals_by_id(movie["tmdb_id"], movie["title"])

    if image_paths:
        logger.info("Uploading %d visuals to temp storage...", len(image_paths))
        for path in image_paths:
            try:
                upload_link = upload_to_temp(path)
                logger.info("🔗 Uploaded %s -> %s", os.path.basename(path), upload_link)
            except Exception as e:
                logger.error("Failed to upload %s: %s", path, e)
        logger.info("\n🚀 VISUALS UPLOAD SUCCESSFUL!\n")
    else:
        logger.warning("No visuals downloaded — proceeding without images.")

    # 5. Log as posted so it won't appear again
    log_posted_movie(movie["tmdb_id"], movie["title"])
    logger.info("✅ Movie logged as posted: %s", movie["title"])

    logger.info("━━━ Filmden Run Complete ━━━")


if __name__ == "__main__":
    run()
