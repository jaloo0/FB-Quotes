import os
import logging
import random
from dotenv import load_dotenv

# Load local .env file immediately
load_dotenv()

from filmden.db.schema import (
    init_db, playlist_count, get_conn, get_genres_with_pending_videos,
    get_pending_video, mark_movie
)
from filmden.pipeline.sync_playlists import sync_playlists
from filmden.pipeline.sync_videos import sync_videos_for_playlist
from filmden.pipeline.extract_movies import process_pending_videos
from filmden.pipeline.pick_movie import pick_movie_to_post
from filmden.pipeline.fetch_visuals import download_movie_visuals
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from pipeline.temp_uploader import upload_to_temp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] filmden: %(message)s")
logger = logging.getLogger("filmden")

def run():
    logger.info("━━━ Filmden Run Started ━━━")
    
    # 1. Initialize DB
    init_db()

    # 2. Check if we need to sync playlists (first run)
    if playlist_count() == 0:
        logger.info("Database is empty. Running initial playlist sync...")
        sync_playlists()

    # 3. Try to pick a movie
    movie = pick_movie_to_post()
    
    # 4. If no movies are available, we need to generate some
    if not movie:
        logger.info("No pending movies found. Attempting to extract movies from pending videos...")
        # Try extracting movies from already synced videos
        process_pending_videos()
        
        movie = pick_movie_to_post()
        
        # 5. If still no movies, we might need to fetch new videos for a playlist
        if not movie:
            logger.info("Still no movies. Attempting to fetch videos for a pending playlist...")
            with get_conn() as conn:
                # Find a playlist that hasn't been synced recently
                pending_playlist = conn.execute("""
                    SELECT playlist_id, genre FROM playlists 
                    WHERE status = 'pending' 
                    ORDER BY RANDOM() LIMIT 1
                """).fetchone()
                
            if pending_playlist:
                sync_videos_for_playlist(pending_playlist["playlist_id"], pending_playlist["genre"])
                # Mark playlist as 'using' or 'used'
                with get_conn() as conn:
                    conn.execute("UPDATE playlists SET status='used' WHERE playlist_id=?", (pending_playlist["playlist_id"],))
                    conn.commit()
                
                # Now extract movies from the newly synced videos
                process_pending_videos()
                movie = pick_movie_to_post()
            else:
                logger.warning("No pending playlists available. We might need to run sync_playlists again.")

    if movie:
        logger.info("🎉 Ready to post about movie: %s", movie["movie_name"])
        logger.info("Genre: %s", movie["genre"])
        logger.info("Details: %s", movie["details"])
        
        # Mark as using during posting process
        mark_movie(movie["id"], "using")
        
        # Fetch Visuals from TMDB
        image_paths = download_movie_visuals(movie["movie_name"])
        
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
            logger.warning("Proceeding without visuals as they could not be downloaded.")
        
        # After successful post:
        mark_movie(movie["id"], "used")
        logger.info("Movie marked as used.")
    else:
        logger.error("Failed to find or generate a movie to post.")

    logger.info("━━━ Filmden Run Complete ━━━")

if __name__ == "__main__":
    run()
