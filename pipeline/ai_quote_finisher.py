"""
ai_quote_finisher.py
--------------------
Takes a raw seed quote + image tags and "finishes the thought" using
the Google Gemini API (free tier).  Falls back to the local engine
if the API is unavailable / quota hit.
"""

import os
import logging
import random

logger = logging.getLogger(__name__)

# ─── Gemini (free) ────────────────────────────────────────────────────────────
def _gemini_finish(seed: str, tags: list[str], vibe: str) -> str | None:
    """Call Gemini Flash (free tier) to stylise the quote fragment."""
    try:
        import google.generativeai as genai  # pip install google-generativeai

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")

        tag_str = ", ".join(tags[:8]) if tags else "cinematic, dark"
        prompt = (
            f"You are writing short, punchy social-media captions in a "
            f"fragmented, lowercase, minimal style — like: "
            f"'damn, i lost again.' or 'still standing. quietly.'.\n\n"
            f"Vibe: {vibe}\n"
            f"Image mood words: {tag_str}\n"
            f"Seed phrase: \"{seed}\"\n\n"
            f"Finish or rephrase this into ONE punchy 1–2 line caption "
            f"(max 15 words total). Keep it lowercase. No hashtags. "
            f"End with a single word or short phrase that lands hard."
        )
        response = model.generate_content(prompt)
        text = response.text.strip().strip('"').strip("'")
        # Sanity: must be short
        if len(text) <= 120:
            return text
        logger.warning("Gemini response too long (%d chars), using fallback.", len(text))
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini API error: %s", exc)
        return None


def get_ai_quote(seed: str, tags: list[str], vibe: str, closer: str) -> str:
    """
    Try AI finishing first; if it fails, assemble locally.
    Returns the final caption string.
    """
    # Try Gemini if key is set
    if os.environ.get("GEMINI_API_KEY"):
        result = _gemini_finish(seed, tags, vibe)
        if result:
            return result

    # Local fallback: seed + closer
    if random.random() < 0.5:
        return f"{seed} {closer}"
    return f"{seed}.\n{closer}"
