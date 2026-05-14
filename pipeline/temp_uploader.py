"""
temp_uploader.py
----------------
Multi-service temporary uploader. Tries multiple providers to ensure
the user gets a test link even if one service is down.
Providers: Catbox, GoFile, File.io
"""

import logging
import requests
import os

logger = logging.getLogger(__name__)

def upload_catbox(image_path: str) -> str | None:
    """Upload to catbox.moe - very reliable for images."""
    url = "https://catbox.moe/user/api.php"
    try:
        logger.info("Trying Catbox.moe...")
        with open(image_path, "rb") as f:
            data = {"reqtype": "fileupload"}
            files = {"fileToUpload": f}
            resp = requests.post(url, data=data, files=files, timeout=30)
        
        if resp.status_code == 200 and "https://" in resp.text:
            link = resp.text.strip()
            logger.info("Catbox link: %s", link)
            return link
    except Exception as e:
        logger.warning("Catbox failed: %s", e)
    return None

def upload_gofile(image_path: str) -> str | None:
    """Upload to GoFile.io - robust and professional."""
    try:
        logger.info("Trying GoFile.io...")
        # 1. Get best server
        server_resp = requests.get("https://api.gofile.io/getServer", timeout=10)
        server_resp.raise_for_status()
        server = server_resp.json()["data"]["server"]
        
        # 2. Upload
        url = f"https://{server}.gofile.io/uploadFile"
        with open(image_path, "rb") as f:
            files = {"file": f}
            resp = requests.post(url, files=files, timeout=40)
        
        resp.raise_for_status()
        data = resp.json()
        if data["status"] == "ok":
            link = data["data"]["downloadPage"]
            logger.info("GoFile link: %s", link)
            return link
    except Exception as e:
        logger.warning("GoFile failed: %s", e)
    return None

def upload_file_io(image_path: str) -> str | None:
    """Upload to file.io - tries to fix the previous issue."""
    url = "https://file.io"
    try:
        logger.info("Trying File.io...")
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
            resp = requests.post(url, files=files, timeout=20)
        
        # If we got HTML (Gatsby), it failed
        if "<html>" in resp.text:
            logger.warning("File.io returned HTML instead of API response.")
            return None
            
        data = resp.json()
        if data.get("success"):
            return data.get("link")
    except Exception as e:
        logger.warning("File.io failed: %s", e)
    return None

def upload_to_temp(image_path: str) -> str:
    """Tries multiple services until one works."""
    # Priority order: Catbox (direct image link) > GoFile (nice UI) > File.io
    providers = [upload_catbox, upload_gofile, upload_file_io]
    
    for provider in providers:
        link = provider(image_path)
        if link:
            return link
            
    raise Exception("All temporary upload services failed.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python temp_uploader.py <path_to_image>")
    else:
        logging.basicConfig(level=logging.INFO)
        p = os.path.abspath(sys.argv[1])
        try:
            link = upload_to_temp(p)
            print(f"\n✅ SUCCESS: {link}")
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
