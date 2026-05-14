import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def upload_file_to_temp_storage(file_path):
    """
    Uploads a file to temporary cloud storage using multiple fallback providers.
    Providers: Pixeldrain -> GoFile -> Litterbox
    
    Returns:
        str: The download link if successful, None otherwise.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None

    filename = os.path.basename(file_path)
    
    # --- PRIMARY: pixeldrain.com ---
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
        else:
            logger.warning(f"⚠️ Pixeldrain failed (HTTP {response.status_code}). Trying GoFile...")
    except Exception as e:
        logger.warning(f"⚠️ Pixeldrain failed: {e}. Trying GoFile...")

    # --- FALLBACK 1: GoFile ---
    logger.info("☁️ Attempting upload to GoFile...")
    try:
        # First, we need to get the best server for GoFile
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
        logger.warning("⚠️ GoFile server selection or upload failed. Trying Litterbox...")
    except Exception as e:
        logger.warning(f"⚠️ GoFile failed: {e}. Trying Litterbox...")

    # --- FALLBACK 2: litterbox.catbox.moe (72h expiry) ---
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
        else:
            logger.warning(f"⚠️ Litterbox failed: HTTP {response.status_code}. Trying file.io...")
    except Exception as e:
        logger.warning(f"⚠️ Litterbox failed: {e}. Trying file.io...")

    # --- FALLBACK 3: file.io (1 download, 2 weeks expiry) ---
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
        else:
            logger.error("❌ file.io failed.")
    except Exception as e:
        logger.error(f"❌ All uploaders failed: {e}")

    return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python upload_file_skill.py <file_path>")
        sys.exit(1)
    
    file_to_upload = sys.argv[1]
    result = upload_file_to_temp_storage(file_to_upload)
    if result:
        print(f"File uploaded successfully: {result}")
    else:
        print("Failed to upload file.")
