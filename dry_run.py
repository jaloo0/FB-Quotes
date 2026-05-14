"""
dry_run.py
----------
Local test: fetches an image, generates a quote, applies all three styles,
saves results to tmp_assets/ — but does NOT post to Facebook.

Usage:
    python dry_run.py [--vibe Defeat|Resilience|Peak|Mystery]
"""

import argparse
import logging
import random
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load local .env file if it exists
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dry_run")

from pipeline.vibe_engine import roll_vibe, get_search_term, get_quote, tags_match_vibe, VIBES
from pipeline.image_fetcher import fetch_image_for_vibe
from pipeline.ai_quote_finisher import get_ai_quote
from pipeline.style_engine import (
    style_big_left,
    style_cinematic_sub,
    style_giant_invert,
    OUTPUT_DIR,
)

OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vibe", choices=list(VIBES.keys()), default=None)
    args = parser.parse_args()

    vibe = args.vibe or roll_vibe()
    logger.info("Vibe: %s", vibe)

    query = get_search_term(vibe)
    logger.info("Query: %s", query)

    result = fetch_image_for_vibe(query=query, vibe=vibe, tags_match_fn=tags_match_vibe)
    if result is None:
        logger.error("No image found.")
        return

    img_path, tags = result
    logger.info("Image: %s | Tags: %s", img_path, tags[:10])

    vibe_data = VIBES[vibe]
    seed = random.choice(vibe_data["quote_seeds"])
    closer = random.choice(vibe_data["closers"])
    quote = get_ai_quote(seed=seed, tags=tags, vibe=vibe, closer=closer)
    logger.info("Quote: %r", quote)

    run_id = uuid.uuid4().hex[:8]

    # Apply ALL three styles for comparison
    paths = {}
    paths["BigLeft"] = style_big_left(img_path, quote, OUTPUT_DIR / f"test_{run_id}_BigLeft.jpg")
    paths["CinematicSub"] = style_cinematic_sub(img_path, quote, OUTPUT_DIR / f"test_{run_id}_CinematicSub.jpg")
    paths["GiantInvert"] = style_giant_invert(img_path, quote, OUTPUT_DIR / f"test_{run_id}_GiantInvert.jpg")

    print("\n✅ Dry run complete. Output files:")
    for style, p in paths.items():
        print(f"   Style {style}: {p.resolve()}")
    print(f"\n   Quote used: {quote!r}")
    print(f"   Vibe:        {vibe}")


if __name__ == "__main__":
    main()
