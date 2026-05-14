"""
temp_uploader.py
----------------
Multi-service temporary uploader based on the user's preferred flow.
Tries Pixeldrain -> GoFile -> Litterbox -> File.io
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

def upload_pixeldrain(file_path: str, filename: str) -> str | None:
    """PRIMARY: pixeldrain.com"""
    logger.info("📤 Attempting upload to pixeldrain.com...")
    try:
        with open(file_path, "rb") as f:
            response = requests.put(
                f"https://pixeldrain.com/api/file/{filename}",
                data=f,
                headers={"Content-Type": "application/octet-stream"},
                timeout=300
            )
        if response.status_code == 201:
            file_id = response.json().get("id")
            link = f"https://pixeldrain.com/u/{file_id}"
            logger.info(f"✅ Pixeldrain Success: {link}")
            return link
    except Exception as e:
        logger.warning(f"⚠️ Pixeldrain failed: {e}")
    return None

def upload_gofile(file_path: str, filename: str) -> str | None:
    """FALLBACK 1: GoFile"""
    logger.info("☁️ Attempting upload to GoFile...")
    try:
        server_response = requests.get("https://api.gofile.io/servers", timeout=10).json()
        if server_response.get("status") == "ok":
            server = server_response["data"]["servers"][0]["name"]
            upload_url = f"https://{server}.gofile.io/contents/uploadfile"
            
            with open(file_path, "rb") as f:
                response = requests.post(
                    upload_url,
                    files={"file": (filename, f)},
                    timeout=300
                ).json()
            
            if response.get('status') == 'ok':
                link = response['data']['downloadPage']
                logger.info(f"✅ GoFile Success: {link}")
                return link
    except Exception as e:
        logger.warning(f"⚠️ GoFile failed: {e}")
    return None

def upload_litterbox(file_path: str, filename: str) -> str | None:
    """FALLBACK 2: litterbox.catbox.moe (72h expiry)"""
    logger.info("📦 Attempting upload to litterbox.catbox.moe...")
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": (filename, f)},
                timeout=300
            )
        if response.status_code == 200:
            link = response.text.strip()
            logger.info(f"✅ Litterbox Success: {link}")
            return link
    except Exception as e:
        logger.warning(f"⚠️ Litterbox failed: {e}")
    return None

def upload_file_io(file_path: str, filename: str) -> str | None:
    """FALLBACK 3: file.io (1 download, 2 weeks expiry)"""
    logger.info("📁 Attempting upload to file.io...")
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://file.io",
                files={"file": (filename, f)},
                timeout=300
            ).json()
        if response.get("success"):
            link = response["link"]
            logger.info(f"✅ file.io Success: {link}")
            return link
    except Exception as e:
        logger.warning(f"⚠️ file.io failed: {e}")
    return None

def upload_to_temp(file_path: str) -> str:
    """Main entry point: tries all providers in order."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    
    providers = [
        upload_pixeldrain,
        upload_gofile,
        upload_litterbox,
        upload_file_io
    ]
    
    for provider in providers:
        link = provider(file_path, filename)
        if link:
            return link
            
    raise Exception("❌ All temporary uploaders failed.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python temp_uploader.py <file_path>")
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        try:
            res = upload_to_temp(sys.argv[1])
            print(f"Final Link: {res}")
        except Exception as e:
            print(e)
