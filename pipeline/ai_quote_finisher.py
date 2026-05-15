"""
ai_quote_finisher.py
--------------------
Takes a raw seed quote + image tags and "finishes the thought" using
OpenRouter API (free tier models).
Falls back to local engine if the API is unavailable / quota hit.

OpenRouter is OpenAI-compatible — no extra package needed beyond requests.
"""

import os
import logging
import random
import requests

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"

# Free models on OpenRouter, tried in order until one succeeds.
# All are strong at short creative writing.
FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",   # Best all-round writer
    "deepseek/deepseek-chat-v3-0324:free",       # Excellent at stylised text
    "google/gemma-3-27b-it:free",                # Good fallback
    "mistralai/mistral-7b-instruct:free",        # Lightweight fallback
]


def _openrouter_finish(seed: str, tags: list[str], vibe: str, style_key: str) -> str | None:
    """Call OpenRouter with free models to stylise the quote fragment."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — using local fallback.")
        return None

    tag_str = ", ".join(tags[:8]) if tags else "cinematic, dark"
    
    # Map style_key to specific "Voice of Vide" constraints
    if style_key == "GiantInvert":
        style_instruction = (
            "Style: INTERNAL MONOLOGUE (Short/Punchy).\n"
            "Constraint: VERY SHORT (under 15 characters total). Max 3 words.\n"
            "Tone: Raw, reactive. lowercase for sad; ALL CAPS for defiant."
        )
    elif style_key == "BigLeft":
        style_instruction = (
            "Style: DEFIANT / HERO (The Left Stack).\n"
            "Constraint: 15 to 40 characters total. 4-7 words.\n"
            "Tone: Bold, strong presence, defiant."
        )
    else:  # CinematicSub
        style_instruction = (
            "Style: MODERN SAGE (Advice/Wisdom).\n"
            "Constraint: LONG (over 40 characters). 10-20 words.\n"
            "Tone: Stoic, calm, grammatically correct. Capitalize first letter."
        )

    prompt = (
        f"You are writing social media captions in 'The Voice of Vide'.\n"
        f"Mood Context: {vibe} ({tag_str})\n"
        f"Seed: \"{seed}\"\n\n"
        f"MANDATORY INSTRUCTIONS:\n{style_instruction}\n\n"
        f"Return ONLY the caption text. No hashtags. No quotes."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/jaloo0/FB-Quotes",
        "X-Title": "FB-Quotes Bot",
        "Content-Type": "application/json",
    }

    for model in FREE_MODELS:
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 60,
                "temperature": 0.85,
            }
            resp = requests.post(
                OPENROUTER_BASE,
                headers=headers,
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            text = text.strip('"').strip("'")
            
            # Simple validation: if it doesn't meet the length, try next model/retry
            if style_key == "GiantInvert" and len(text) > 20: continue
            if style_key == "CinematicSub" and len(text) < 30: continue

            logger.info("OpenRouter (%s) quote for %s: %r", model, style_key, text)
            return text
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenRouter model %s failed: %s", model, exc)
            continue

    return None


def get_ai_quote(seed: str, tags: list[str], vibe: str, closer: str, style_key: str) -> str:
    """
    Try OpenRouter AI first; if all models fail, assemble locally.
    Returns the final caption string.
    """
    result = _openrouter_finish(seed, tags, vibe, style_key)
    if result:
        return result

    # Local fallback
    if style_key == "GiantInvert":
        return seed.lower() if "lowercase" in vibe.lower() else seed.upper()
    return f"{seed} {closer}"
