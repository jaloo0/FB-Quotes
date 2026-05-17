"""
Quick diagnostic: Fetches playlists from @MoviesBolt using the YouTube Data API.
Run: python filmden/test_playlists.py
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

API_KEY = os.getenv("YT_API_KEY")
CHANNEL_ID = "UC3_0SghtWdDi5faLpl2xgaQ"

if not API_KEY:
    print("ERROR: YT_API_KEY not found in .env!")
    exit(1)

import sys
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
print(f"Using API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
print(f"Channel ID: {CHANNEL_ID}")
print("-" * 50)

url = "https://www.googleapis.com/youtube/v3/playlists"
params = {
    "part": "snippet",
    "channelId": CHANNEL_ID,
    "maxResults": 10,
    "key": API_KEY,
}

print(f"Requesting: {url}")
print(f"Params (key hidden): {dict(part=params['part'], channelId=params['channelId'], maxResults=params['maxResults'])}")
print("-" * 50)

try:
    resp = requests.get(url, params=params, timeout=30)
    print(f"HTTP Status: {resp.status_code}")
    data = resp.json()
    
    if resp.status_code == 200:
        items = data.get("items", [])
        print(f"\nSUCCESS! Found {len(items)} playlists:")
        for pl in items:
            print(f"  - [{pl['id']}] {pl['snippet']['title']}")
        total = data.get("pageInfo", {}).get("totalResults", "?")
        print(f"\nTotal playlists on channel: {total}")
    else:
        print(f"\nFAILED:")
        error = data.get("error", {})
        print(f"  Code: {error.get('code')}")
        print(f"  Message: {error.get('message')}")
        print(f"  Reason: {error.get('errors', [{}])[0].get('reason')}")

except Exception as e:
    print(f"\nCONNECTION ERROR: {e}")
