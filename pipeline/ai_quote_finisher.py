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


def _openrouter_finish(seed: str, tags: list[str], vibe: str) -> str | None:
    """Call OpenRouter with free models to stylise the quote fragment."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — using local fallback.")
        return None

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
            if len(text) <= 120:
                logger.info("OpenRouter (%s) quote: %r", model, text)
                return text
            logger.warning("Model %s response too long (%d chars).", model, len(text))
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenRouter model %s failed: %s", model, exc)
            continue

    return None


def get_ai_quote(seed: str, tags: list[str], vibe: str, closer: str) -> str:
    """
    Try OpenRouter AI first; if all models fail, assemble locally.
    Returns the final caption string.
    """
    result = _openrouter_finish(seed, tags, vibe)
    if result:
        return result

    # Local fallback: seed + closer
    if random.random() < 0.5:
        return f"{seed} {closer}"
    return f"{seed}.\n{closer}"
