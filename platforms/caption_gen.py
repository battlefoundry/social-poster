"""Generates a fresh caption using Google's free Gemini API. Raises on any
failure -- the caller is expected to catch that and fall back to a static
caption list, so a Gemini outage never blocks a post."""
import random
import requests

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-lite:generateContent"
)

LINKS_BLOCK = """Fantasy: https://cults3d.com/@BattleFoundry
Scifi: https://cults3d.com/@BATTLEFOUNDRYSCIFI
Grimdark: https://cults3d.com/@DREADWORKS
Resin Statue: https://cults3d.com/@BlacksiteSyndicate"""

PROMO_PROMPT = """You write short, punchy social media captions for a free \
tabletop-miniature STL store called BattleFoundry (fantasy + sci-fi minis) \
and Blacksite Syndicate (resin statues), posting on Bluesky and Mastodon.

Write ONE new caption (2-3 sentences max, casual and enthusiastic, not \
corporate-sounding) promoting that the miniatures are FREE to download. Do \
NOT include any links or hashtags -- those get added separately. Do not \
wrap your answer in quotation marks. Return only the caption text, nothing \
else."""

ENGAGEMENT_PROMPT = """You run social media for a tabletop-miniature / \
3D-printing hobby store on Bluesky and Mastodon. Write ONE short, casual \
post (1-2 sentences) meant to spark replies from the D&D / tabletop \
wargaming / 3D-printing community -- a question, a hot-take prompt, or a \
quick printing tip. Do NOT include any links. Do not wrap your answer in \
quotation marks. Return only the text, nothing else."""

HASHTAG_SETS = [
    "#dnd #ttrpg #tabletopwargame #3dprinting #stl #freeminiatures",
    "#stl #3dprinting #dnd #ttrpg #freeminiatures",
    "#tabletopwargame #dnd #ttrpg #3dprinting #freeminiatures",
    "#freeminiatures #dnd #ttrpg #3dprinting #tabletopwargame",
]

ENGAGEMENT_TAGS = "#dnd #ttrpg #tabletopwargame #3dprinting"


def _call_gemini(api_key: str, prompt: str) -> str:
    resp = requests.post(
        GEMINI_URL,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if not text:
        raise RuntimeError("Gemini returned an empty caption")
    return text


def generate_caption(api_key: str, kind: str) -> str:
    """kind is 'promo' or 'engagement'."""
    if kind == "promo":
        body = _call_gemini(api_key, PROMO_PROMPT)
        return f"{body}\n\n{LINKS_BLOCK}\n\n{random.choice(HASHTAG_SETS)}"
    else:
        body = _call_gemini(api_key, ENGAGEMENT_PROMPT)
        return f"{body}\n\n{ENGAGEMENT_TAGS}"
