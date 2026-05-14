"""
temp_uploader.py
----------------
Uploads an image to file.io (temporary storage) and returns the link.
Useful for testing when Facebook API is disconnected or failing.
"""

import logging
import requests

logger = logging.getLogger(__name__)

def upload_to_temp(image_path: str) -> str:
    """
    Uploads the file to file.io and returns the public link.
    Expires after 1 view or 14 days by default.
    """
    url = "https://file.io"
    logger.info("Uploading %s to file.io...", image_path)
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        # Use a 1-week expiry just in case
        params = {"expires": "1w"}
        resp = requests.post(url, files=files, data=params, timeout=30)
        
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        logger.error("Failed to decode JSON from file.io. Status: %d, Content: %r", resp.status_code, resp.text)
        raise

    if data.get("success"):
        link = data.get("link")
        logger.info("Temporary link: %s", link)
        return link
    else:
        logger.error("Upload failed: %s", data)
        raise Exception(f"File.io upload failed: {data}")

if __name__ == "__main__":
    import sys
    import os
    if len(sys.argv) < 2:
        print("Usage: python temp_uploader.py <path_to_image>")
    else:
        logging.basicConfig(level=logging.INFO)
        # Fix path if relative
        p = sys.argv[1]
        if not os.path.isabs(p):
            p = os.path.abspath(p)
        upload_to_temp(p)
