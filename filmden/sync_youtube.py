import os
import sqlite3
import requests

# Configuration
YOUTUBE_API_KEY = os.getenv("YT_API_KEY")
# Official channel ID for @MoviesBolt
CHANNEL_ID = "UC3_0SghtWdDi5faLpl2xgaQ"
DB_NAME = "movies_db.sqlite"

def init_db():
    """Initializes the built-in SQLite database and creates tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table to store playlists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            playlist_id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT
        )
    ''')
    
    # Table to store individual video/movie suggestions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_suggestions (
            video_id TEXT PRIMARY KEY,
            playlist_id TEXT,
            video_title TEXT,
            description TEXT,
            is_posted INTEGER DEFAULT 0,
            FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def fetch_all_playlists():
    """Retrieves all playlists from the specified channel using pagination."""
    playlists = []
    url = "https://www.googleapis.com/youtube/v3/playlists"
    params = {
        "part": "snippet",
        "channelId": CHANNEL_ID,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
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
                    print(f"Error {response.status_code}: {response.text}")
                    break
            except Exception as e:
                print(f"Connection attempt {attempt+1} failed: {e}")
        
        if not success:
            break
            
        data = response.json()
        for item in data.get("items", []):
            playlists.append({
                "id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"]
            })
            
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token

    return playlists

def fetch_playlist_videos(playlist_id):
    """Retrieves all video items within a specific playlist using pagination."""
    videos = []
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
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
                    print(f"Error {response.status_code}: {response.text}")
                    break
            except Exception as e:
                print(f"Connection attempt {attempt+1} failed: {e}")

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
                    "description": snippet["description"]
                })
                
        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token

    return videos

def save_data_to_db(playlists_data):
    """Saves playlists and videos cleanly to SQLite, avoiding duplicates."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for pl in playlists_data:
        # Insert playlist if it doesn't exist
        cursor.execute('''
            INSERT OR IGNORE INTO playlists (playlist_id, title, description)
            VALUES (?, ?, ?)
        ''', (pl["id"], pl["title"], pl["description"]))
        
        print(f"Syncing videos from playlist: {pl['title']}")
        videos = fetch_playlist_videos(pl["id"])
        
        for video in videos:
            # Insert video if it doesn't exist (leaves 'is_posted' unchanged if it does)
            cursor.execute('''
                INSERT OR IGNORE INTO video_suggestions (video_id, playlist_id, video_title, description)
                VALUES (?, ?, ?, ?)
            ''', (video["video_id"], pl["id"], video["title"], video["description"]))
            
    conn.commit()
    conn.close()
    print("Database sync completed successfully.")

if __name__ == "__main__":
    if not YOUTUBE_API_KEY:
        print("CRITICAL ERROR: YT_API_KEY environment variable is not set.")
    else:
        init_db()
        print("Fetching playlists...")
        all_playlists = fetch_all_playlists()
        print(f"Found {len(all_playlists)} playlists. Syncing items...")
        save_data_to_db(all_playlists)