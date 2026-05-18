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
import re
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


def _clean_quote_text(text: str) -> str:
    """
    Cleans up any stubborn typos or grammar issues from the AI output.
    Specifically targets:
      - 'quite' instead of 'quiet' (e.g. quite money -> quiet money, quite people -> quiet people, etc.)
      - Subject-verb agreement (e.g. quiet people knows -> quiet people know, people knows -> people know)
      - Strips accidental extra quotes and excessive whitespace.
    """
    if not text:
        return text

    # Strip surrounding quotes and whitespace
    text = text.strip().strip('"').strip("'").strip()

    # Define common typo corrections (case-insensitive regex)
    replacements = {
        r"\bquite\s+money\b": "quiet money",
        r"\bquite\s+people\b": "quiet people",
        r"\bquite\s+ones\b": "quiet ones",
        r"\bquite\s+one\b": "quiet one",
        r"\bquite\s+moment\b": "quiet moment",
        r"\bquite\s+place\b": "quiet place",
        r"\bquite\s+room\b": "quiet room",
        r"\bquite\s+night\b": "quiet night",
        r"\bquite\s+exit\b": "quiet exit",
        r"\bquite\s+life\b": "quiet life",
        r"\bquite\s+side\b": "quiet side",
        r"\bquite\s+man\b": "quiet man",
        r"\bquite\s+woman\b": "quiet woman",
        r"\bquite\s+warrior\b": "quiet warrior",
        r"^quite\s+": "quiet ",
        r"\bquite\s+enough\b": "quiet enough",
        
        # Subject-verb agreement corrections:
        r"\bpeople\s+knows\b": "people know",
        r"\bpeople\s+has\b": "people have",
        r"\bpeople\s+is\b": "people are",
        r"\bthe\s+quiet\s+ones\s+knows\b": "the quiet ones know",
        r"\bthe\s+quiet\s+ones\s+has\b": "the quiet ones have",
        r"\bthe\s+quiet\s+ones\s+is\b": "the quiet ones are",
        r"\bones\s+always\s+knows\b": "ones always know",
        
        # General typo 'quite' when used at end of clause / as predicate:
        r"\bis\s+quite\b": "is quiet",
        r"\bbe\s+quite\b": "be quiet",
        r"\bthis\s+quite\b": "this quiet",
        r"\bso\s+quite\b": "so quiet",
        r"\bvery\s+quite\b": "very quiet",
        r"\btoo\s+quite\b": "too quiet",
    }

    cleaned = text
    for pattern, repl in replacements.items():
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)

    # Strip any stray leading/trailing quotes
    cleaned = cleaned.strip('"').strip("'").strip()
    return cleaned


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
        f"CRITICAL QUALITY RULES:\n"
        f"- Ensure flawless spelling, grammar, and sentence structure.\n"
        f"- NEVER confuse the word 'quiet' (silent, calm, stillness) with 'quite' (completely, very). If you write about sound level, silence, or calm, ALWAYS write 'quiet' (e.g. 'quiet money', 'quiet people', 'quiet ones', 'quiet exit').\n"
        f"- Ensure subject-verb agreement (e.g., 'people know' NOT 'people knows', 'ones know' NOT 'ones knows').\n"
        f"- Avoid clichés or directly echoing the seed word-for-word if it makes the caption repetitive or grammatically awkward.\n\n"
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
            text = _clean_quote_text(text)
            
            # Simple validation: if it doesn't meet the length, try next model/retry
            if style_key == "GiantInvert" and len(text) > 20: continue
            if style_key == "CinematicSub" and len(text) < 30: continue

            logger.info("OpenRouter (%s) quote for %s: %r", model, style_key, text)
            return text
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenRouter model %s failed: %s", model, exc)
            continue

    return None


def get_ai_quote(seed: str, tags: list[str], vibe: str, closer: str, style_key: str = "CinematicSub") -> str:
    """
    Try OpenRouter AI first; if all models fail, assemble locally.
    Returns the final caption string.
    """
    result = _openrouter_finish(seed, tags, vibe, style_key)
    if result:
        return _clean_quote_text(result)

    # Local fallback
    if style_key == "GiantInvert":
        local_quote = seed.lower() if "lowercase" in vibe.lower() else seed.upper()
    else:
        local_quote = f"{seed} {closer}"
        
    return _clean_quote_text(local_quote)
