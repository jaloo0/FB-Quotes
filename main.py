"""
main.py
-------
Orchestrator – runs the full pipeline end-to-end:

  1. Roll a Vibe
  2. Fetch a matching image from Pexels
  3. Generate / AI-finish the quote
  4. Apply a random visual style
  5. Post to Facebook
  6. Cleanup temp files
"""

import logging
import random
import shutil
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load local .env file if it exists
load_dotenv()

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

from pipeline.vibe_engine import (
    roll_vibe,
    get_search_term,
    get_quote,
    tags_match_vibe,
    get_unused_seed,
    VIBES,
)
from pipeline.image_fetcher import fetch_image_for_vibe
from pipeline.ai_quote_finisher import get_ai_quote
from pipeline.style_engine import apply_random_style
# from pipeline.fb_poster import post_photo  # FB Disconnected
from pipeline.temp_uploader import upload_to_temp

TMP_DIR = Path("tmp_assets")


def cleanup():
    """Delete all temporary assets."""
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
        logger.info("Cleaned up %s", TMP_DIR)


def run():
    run_id = uuid.uuid4().hex[:8]
    logger.info("━━━ Run %s started ━━━", run_id)

    # ── 1. Roll Vibe & Style ──────────────────────────────────────────────────
    vibe = roll_vibe()
    # Pick a target visual style first
    style_key = random.choice(["GiantInvert", "BigLeft", "CinematicSub"])
    logger.info("Vibe: %s | Target Style: %s", vibe, style_key)

    # ── 2. Fetch Image ────────────────────────────────────────────────────────
    query = get_search_term(vibe)
    logger.info("Pexels query: %s", query)

    result = fetch_image_for_vibe(
        query=query,
        vibe=vibe,
        tags_match_fn=tags_match_vibe,
    )
    if result is None:
        logger.error("Could not fetch a suitable image. Aborting.")
        return

    img_path, tags = result
    logger.info("Image: %s | Tags: %s", img_path, tags)

    # ── 3. Generate Quote (Specific to Style) ─────────────────────────────────
    vibe_data = VIBES[vibe]
    seed = get_unused_seed(vibe, tags)
    closer = random.choice(vibe_data["closers"])

    # Pass style_key to AI so it writes the correct length/tone
    quote = get_ai_quote(seed=seed, tags=tags, vibe=vibe, closer=closer, style_key=style_key)
    logger.info("Quote (%d chars): %r", len(quote), quote)

    # ── 4. Apply Visual Style ─────────────────────────────────────────────────
    final_img = apply_random_style(img_path, quote, run_id, style_key=style_key)
    logger.info("Final image: %s", final_img)

    # ── 5. Upload to Temp Storage ─────────────────────────────────────────────
    try:
        # post_photo(str(final_img), quote, vibe)
        # logger.info("Posted successfully.")
        link = upload_to_temp(str(final_img))
        print(f"\n🚀 TEST UPLOAD SUCCESSFUL!")
        print(f"🔗 View your image here: {link}\n")
    except Exception as exc:  # noqa: BLE001
        logger.error("Upload failed: %s", exc)

    # ── 6. Cleanup ────────────────────────────────────────────────────────────
    cleanup()
    logger.info("━━━ Run %s complete ━━━", run_id)


if __name__ == "__main__":
    run()
