"""Generates a longer blog-style post using Google's free Gemini API."""
import requests

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

BLOG_PROMPT = """You write blog posts for BattleFoundry, a hobby brand offering \
free tabletop-miniature STL files (fantasy under BattleFoundry, sci-fi under \
BATTLEFOUNDRYSCIFI, grimdark under DREADWORKS) and resin statues under \
Blacksite Syndicate, all downloadable free from Cults3D.

Write ONE short blog post (3-4 short paragraphs, casual and enthusiastic, \
like a hobbyist talking to other hobbyists -- not corporate). Cover things \
like: what kind of miniature this could be used for in a D&D or wargaming \
campaign, a printing or painting tip, or some flavor/lore imagining the \
miniature in a game. Do NOT include any links, hashtags, or markdown \
formatting -- plain paragraphs only, separated by blank lines.

Return your response in exactly this format, nothing else:
TITLE: <a short catchy title, under 60 characters>
BODY:
<the paragraphs>"""


def _call_gemini(api_key: str, prompt: str) -> str:
    resp = requests.post(
        GEMINI_URL,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    if not text:
        raise RuntimeError("Gemini returned an empty blog post")
    return text


def generate_blog_post(api_key: str) -> dict:
    """Returns {'title': str, 'body': str}."""
    raw = _call_gemini(api_key, BLOG_PROMPT)
    title = "New Free Miniature"
    body = raw
    if "TITLE:" in raw and "BODY:" in raw:
        title_part = raw.split("TITLE:", 1)[1].split("BODY:", 1)[0].strip()
        body_part = raw.split("BODY:", 1)[1].strip()
        if title_part:
            title = title_part
        if body_part:
            body = body_part
    return {"title": title, "body": body}
