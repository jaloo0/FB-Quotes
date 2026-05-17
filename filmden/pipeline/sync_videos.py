import os
import requests
import logging
from filmden.db.schema import insert_video, get_conn, now

logger = logging.getLogger("filmden.pipeline.sync_videos")

def fetch_videos_for_playlist(playlist_id: str):
    """Retrieves all video items within a specific playlist."""
    api_key = os.getenv("YT_API_KEY")
    if not api_key:
        logger.error("YT_API_KEY is not set.")
        return []

    videos = []
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": api_key,
        "pageToken": ""
    }

    while True:
        success = False
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    success = True
                    break
                else:
                    logger.error("Error fetching videos for playlist %s: %s", playlist_id, response.text)
                    break
            except Exception as e:
                logger.warning("Connection attempt %s failed: %s", attempt + 1, e)

        if not success:
            break
            
        data = response.json()
        for item in data.get("items", []):
            snippet = item["snippet"]
            video_id = snippet.get("resourceId", {}).get("videoId")
            if video_id:
                videos.append({
                    "video_id": video_id,
                    "title": snippet["title"],
                })
                
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token

    return videos

def sync_videos_for_playlist(playlist_id: str, genre: str):
    """Fetch videos for a playlist and save them to the database."""
    logger.info("Fetching videos for playlist %s", playlist_id)
    videos = fetch_videos_for_playlist(playlist_id)
    
    total_added = 0
    for video in videos:
        insert_video(video["video_id"], playlist_id, video["title"], genre)
        total_added += 1

    # Mark playlist as synced
    with get_conn() as conn:
        conn.execute("UPDATE playlists SET synced_at=? WHERE playlist_id=?", (now(), playlist_id))
        conn.commit()

    logger.info("Added %d videos for playlist %s.", total_added, playlist_id)
