"""
fb_poster.py
------------
Posts the final image to Facebook via the Graph API.
Requires env vars: FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

# Vibe → relevant hashtag pool
HASHTAGS = {
    "Defeat": ["#RealTalk", "#LowMoment", "#HumanSide"],
    "Resilience": ["#KeepGoing", "#Resilience", "#NeverSettle"],
    "Peak": ["#LevelUp", "#QuietSuccess", "#DifferentBreed"],
    "Mystery": ["#Untold", "#LayersDeep", "#ReadBetween"],
}

GRAPH_BASE = "https://graph.facebook.com/v19.0"


def _page_creds() -> tuple[str, str]:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    return page_id, token


def post_photo(image_path: str, caption: str, vibe: str) -> dict:
    """
    Upload image to Facebook page and publish with caption + hashtags.
    Returns the Graph API response dict.
    """
    page_id, token = _page_creds()

    # Pick 2–3 targeted hashtags
    import random
    tags = random.sample(HASHTAGS.get(vibe, ["#Quotes"]), k=min(3, len(HASHTAGS.get(vibe, ["#Quotes"]))))
    full_caption = f"{caption}\n\n{' '.join(tags)}"

    url = f"{GRAPH_BASE}/{page_id}/photos"
    with open(image_path, "rb") as img_file:
        resp = requests.post(
            url,
            data={
                "caption": full_caption,
                "access_token": token,
                "published": "true",
            },
            files={"source": img_file},
            timeout=30,
        )

    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error("Facebook API Error: %s", resp.text)
        raise e
        
    result = resp.json()
    logger.info("Posted to Facebook: %s", result)
    return result
