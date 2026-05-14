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
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load local .env file if it exists
load_dotenv()

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
    VIBES,
)
from pipeline.image_fetcher import fetch_image_for_vibe
from pipeline.ai_quote_finisher import get_ai_quote
from pipeline.style_engine import apply_random_style
from pipeline.fb_poster import post_photo

TMP_DIR = Path("tmp_assets")


def cleanup():
    """Delete all temporary assets."""
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
        logger.info("Cleaned up %s", TMP_DIR)


def run():
    run_id = uuid.uuid4().hex[:8]
    logger.info("━━━ Run %s started ━━━", run_id)

    # ── 1. Roll Vibe ──────────────────────────────────────────────────────────
    vibe = roll_vibe()
    logger.info("Vibe rolled: %s", vibe)

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

    # ── 3. Generate Quote ─────────────────────────────────────────────────────
    # Pick a seed + closer from local library first
    vibe_data = VIBES[vibe]
    seed = random.choice(vibe_data["quote_seeds"])
    closer = random.choice(vibe_data["closers"])

    quote = get_ai_quote(seed=seed, tags=tags, vibe=vibe, closer=closer)
    logger.info("Quote: %r", quote)

    # ── 4. Apply Visual Style ─────────────────────────────────────────────────
    final_img = apply_random_style(img_path, quote, run_id)
    logger.info("Final image: %s", final_img)

    # ── 5. Post to Facebook ───────────────────────────────────────────────────
    try:
        post_photo(str(final_img), quote, vibe)
        logger.info("Posted successfully.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Facebook post failed: %s", exc)

    # ── 6. Cleanup ────────────────────────────────────────────────────────────
    cleanup()
    logger.info("━━━ Run %s complete ━━━", run_id)


if __name__ == "__main__":
    run()
