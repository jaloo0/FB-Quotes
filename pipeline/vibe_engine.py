"""
vibe_engine.py
--------------
Handles mood selection, Pexels image search terms, and quote fragment library.
Each Vibe maps to:  search_terms, tags (for matching), quote_seeds
"""

import random
import json
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / "assets" / "used_quotes.json"

VIBES = {
    "Defeat": {
        "search_terms": [
            "dark cinematic rain night",
            "gloomy abandoned street night",
            "silhouette alone fog night",
            "empty road night",
            "broken glass dark noir",
        ],
        "tag_hints": [
            "dark", "alone", "rain", "fog", "shadow", "gloomy",
            "abandoned", "sad", "night", "empty", "noir",
        ],
        "quote_seeds": [
            "damn, i lost",
            "tried everything",
            "not again",
            "silence always wins",
            "nobody told me it'd be this quiet",
            "slipped through again",
            "fought hard, lost soft",
            "the count is off",
            "empty pockets, full lessons",
            "gravity won this time",
            "shadows got longer today",
            "a quiet exit from the stage",
            "the noise faded, the reality set in",
            "left it all on the concrete",
            "sometimes the dark is a shield",
            "nothing left to prove to the ghosts",
        ],
        "closers": [
            "again.", "to be continued.", "still.",
            "as expected.", "like always.", "quietly.",
        ],
    },
    "Resilience": {
        "search_terms": [
            "hero silhouette dark sunrise",
            "lone warrior cinematic night",
            "man standing storm night",
            "comeback road dark cinematic",
            "rising figure dark dramatic light",
        ],
        "tag_hints": [
            "hero", "strong", "sunrise", "light", "power",
            "warrior", "rising", "dramatic", "epic", "courage",
        ],
        "quote_seeds": [
            "still breathing",
            "bent but not done",
            "one more round",
            "they counted me out",
            "got up slower this time",
            "back again",
            "scars talk",
            "kept going when it made no sense",
            "dust off the shoulders",
            "the fire didn't consume, it forged",
            "still in the arena",
            "every setback is a setup",
            "built to endure the storm",
            "heavy heart, steady feet",
            "they wanted a tragedy, I gave them a comeback",
            "rising from the ashes, quietly",
        ],
        "closers": [
            "watch.", "not done yet.", "always.",
            "every single time.", "no matter what.", "still standing.",
        ],
    },
    "Peak": {
        "search_terms": [
            "dark cinematic luxury car",
            "penthouse city night",
            "successful man silhouette",
            "cinematic wealth aesthetic",
            "winner golden hour",
        ],
        "tag_hints": [
            "luxury", "success", "golden", "car", "city",
            "winner", "rich", "night", "power", "confidence",
        ],
        "quote_seeds": [
            "top looks different up close",
            "they asked how",
            "quiet money is loud enough",
            "built this alone",
            "nobody was in the room when it happened",
            "different breed",
            "took the long route",
            "all the no's were fuel",
            "success needs no explanation",
            "silent moves make the loudest impact",
            "monuments aren't built in public",
            "they talk, I execute",
            "elevated beyond the noise",
            "class speaks louder than clout",
            "the view is clear from the summit",
            "results are the only resume",
        ],
        "closers": [
            "remember that.", "earned.", "facts.",
            "that's it.", "period.", "no caption needed.",
        ],
    },
    "Mystery": {
        "search_terms": [
            "cinematic dark figure mist",
            "anonymous silhouette night",
            "mysterious shadow city",
            "noir aesthetic cinematic",
            "unknown traveler road",
        ],
        "tag_hints": [
            "mystery", "shadow", "anonymous", "fog", "noir",
            "dark", "unknown", "silhouette", "mist", "hidden",
        ],
        "quote_seeds": [
            "you don't know half of it",
            "layers on layers",
            "not everything needs a label",
            "some chapters are private",
            "the quiet ones always know more",
            "never explained myself",
            "read between",
            "understood by few",
            "hidden in plain sight",
            "the unseen moves are the most powerful",
            "let them wonder",
            "a closed book is a powerful weapon",
            "acting in the dark, shining in the light",
            "not all who wander want to be found",
            "the mask is real, the face is a secret",
            "some paths are meant to be walked alone",
        ],
        "closers": [
            "figure it out.", "not for everyone.", "…",
            "you'll see.", "someday.", "maybe never.",
        ],
    },
}


def roll_vibe() -> str:
    """Randomly select a vibe category."""
    return random.choice(list(VIBES.keys()))


def get_search_term(vibe: str) -> str:
    """Pick a random Pexels search term for the given vibe, enforcing a dark aesthetic."""
    base_term = random.choice(VIBES[vibe]["search_terms"])
    return f"{base_term} dark moody low light"


def get_unused_seed(vibe: str, ai_tags: list[str] | None = None) -> str:
    """
    Load history of used seeds from used_quotes.json.
    Filter the vibe's quote_seeds to avoid repeating them.
    Reset history for the vibe if we are running low on unused seeds (e.g. fewer than 2 left).
    Save the newly selected seed to the history.
    """
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Load existing history
    history = {}
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = {}

    if not isinstance(history, dict):
        history = {}

    used_seeds = history.get(vibe, [])
    if not isinstance(used_seeds, list):
        used_seeds = []

    # 2. Get the list of all available seeds for this vibe
    all_seeds = VIBES[vibe]["quote_seeds"]

    # 3. Filter out used seeds
    available_seeds = [s for s in all_seeds if s not in used_seeds]

    # 4. If we have fewer than 2 unused seeds left, reset the history for this vibe to prevent starvation
    if len(available_seeds) < 2:
        available_seeds = all_seeds
        used_seeds = []

    # 5. Select the seed using _pick_resonant_seed or random selection
    if ai_tags and len(ai_tags) > 0:
        seed = _pick_resonant_seed(available_seeds, ai_tags)
    else:
        seed = random.choice(available_seeds)

    # 6. Save back to history
    used_seeds.append(seed)
    history[vibe] = used_seeds
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to save quote history: %s", e)

    return seed


def get_quote(vibe: str, ai_tags: list[str] | None = None) -> str:
    """
    Generate a punchy, fragmented quote for the vibe.
    
    Uses history tracking to ensure that seeds are not repeated.
    Returns a short 1–2 line quote.
    """
    data = VIBES[vibe]
    closers = data["closers"]

    seed = get_unused_seed(vibe, ai_tags)
    closer = random.choice(closers)

    # 50 % chance: single punchy line vs two-liner
    if random.random() < 0.5:
        return f"{seed} {closer}"
    else:
        return f"{seed}.\n{closer}"


def _pick_resonant_seed(seeds: list[str], tags: list[str]) -> str:
    """Score seeds by overlap with image tags, return best (or random)."""
    tag_set = {t.lower() for t in tags}
    scored = []
    for seed in seeds:
        words = set(seed.lower().split())
        score = len(words & tag_set)
        scored.append((score, seed))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    # If no overlap at all, go random
    if top_score == 0:
        return random.choice(seeds)
    # Among all seeds tied at the top score, pick randomly
    top_seeds = [s for sc, s in scored if sc == top_score]
    return random.choice(top_seeds)


def tags_match_vibe(vibe: str, tags: list[str], threshold: int = 1) -> bool:
    """
    Return True if at least `threshold` image tags overlap with the vibe's
    hint keywords (case-insensitive substring match).
    """
    hints = VIBES[vibe]["tag_hints"]
    tag_text = " ".join(t.lower() for t in tags)
    matches = sum(1 for h in hints if h in tag_text)
    return matches >= threshold
