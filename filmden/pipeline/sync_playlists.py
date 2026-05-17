import os
import requests
import logging
from filmden.db.schema import insert_playlist

logger = logging.getLogger("filmden.pipeline.sync_playlists")

CHANNEL_ID = "UC3_0SghtWdDi5faLpl2xgaQ"

BLACKLIST = [
    "bolt break", "trailer breakdown", "bolt news",
    "movies review in hindi", "shots", "movies explanation in hindi",
    "bolt explained", "trailer review", "box office"
]

GENRE_KEYWORDS = [
    "action", "horror", "comedy", "thriller", "drama", "crime",
    "sci-fi", "romance", "mystery", "animation", "fantasy", "documentary"
]

def extract_genre(title: str) -> str | None:
    """Extract genre from the playlist title."""
    title_lower = title.lower()
    for genre in GENRE_KEYWORDS:
        if genre in title_lower:
            return genre.capitalize()
    return None

def is_blacklisted(title: str) -> bool:
    """Check if the playlist title contains blacklisted keywords."""
    title_lower = title.lower()
    for keyword in BLACKLIST:
        if keyword in title_lower:
            return True
    return False

def sync_playlists():
    """Fetch all playlists from the channel and save to the database."""
    api_key = os.getenv("YT_API_KEY")
    if not api_key:
        logger.error("YT_API_KEY is not set.")
        return

    url = "https://www.googleapis.com/youtube/v3/playlists"
    params = {
        "part": "snippet,contentDetails",
        "channelId": CHANNEL_ID,
        "maxResults": 50,
        "key": api_key,
        "pageToken": ""
    }

    total_added = 0
    total_skipped = 0

    while True:
        success = False
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    success = True
                    break
                else:
                    logger.error("Error %s: %s", response.status_code, response.text)
                    break
            except Exception as e:
                logger.warning("Connection attempt %s failed: %s", attempt + 1, e)
        
        if not success:
            break
            
        data = response.json()
        for item in data.get("items", []):
            playlist_id = item["id"]
            title = item["snippet"]["title"]
            video_count = item.get("contentDetails", {}).get("itemCount", 0)

            if is_blacklisted(title):
                total_skipped += 1
                continue

            genre = extract_genre(title)
            # If no genre is found, you might want to categorize it as 'Unknown' or skip. Let's keep it None for now.
            
            insert_playlist(playlist_id, title, genre, video_count)
            total_added += 1

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token

    logger.info("Playlist sync complete: %d added/updated, %d skipped.", total_added, total_skipped)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    sync_playlists()
