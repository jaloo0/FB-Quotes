"""
vibe_engine.py
--------------
Handles mood selection, Pexels image search terms, and quote fragment library.
Each Vibe maps to:  search_terms, tags (for matching), quote_seeds
"""

import random

VIBES = {
    "Defeat": {
        "search_terms": [
            "dark cinematic rain",
            "gloomy abandoned street",
            "silhouette alone fog",
            "empty road night",
            "broken glass dark",
        ],
        "tag_hints": [
            "dark", "alone", "rain", "fog", "shadow", "gloomy",
            "abandoned", "sad", "night", "empty",
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
        ],
        "closers": [
            "again.", "to be continued.", "still.",
            "as expected.", "like always.", "quietly.",
        ],
    },
    "Resilience": {
        "search_terms": [
            "hero silhouette sunrise",
            "lone warrior cinematic",
            "man standing storm",
            "comeback road cinematic",
            "rising figure dramatic light",
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
    """Pick a random Pexels search term for the given vibe."""
    return random.choice(VIBES[vibe]["search_terms"])


def get_quote(vibe: str, ai_tags: list[str] | None = None) -> str:
    """
    Generate a punchy, fragmented quote for the vibe.

    If ai_tags are provided, we try to pick a seed that semantically
    resonates with those tags (simple keyword overlap), otherwise random.
    Returns a short 1–2 line quote.
    """
    data = VIBES[vibe]
    seeds = data["quote_seeds"]
    closers = data["closers"]

    seed = _pick_resonant_seed(seeds, ai_tags) if ai_tags else random.choice(seeds)
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
