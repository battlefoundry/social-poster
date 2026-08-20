"""Generates blog content using Google's free Gemini API.
Three rotating post types:
  - saga:     an ongoing serialized story, continuing from the last chapter
  - tutorial: standalone painting/printing tips
  - lore:     standalone worldbuilding, unconnected to the saga
"""
import time
import requests

from platforms.brand_voice import VOICE, SEO_KEYWORDS

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 8  # doubles each retry (8s, 16s, 32s)

BRAND_CONTEXT = """BattleFoundry is a tabletop-miniature STL brand: fantasy \
minis under BattleFoundry, sci-fi under BATTLEFOUNDRYSCIFI, grimdark under \
DREADWORKS, and resin statues under Blacksite Syndicate -- all free to \
download from Cults3D."""

FORMAT_RULES = """Do NOT include any links, hashtags, or markdown formatting -- \
plain paragraphs only, separated by blank lines. Return your response in \
exactly this format, nothing else:
TITLE: <a short, sharp title, under 60 characters, written the way a \
hobbyist would search for it>
BODY:
<the paragraphs>"""

SAGA_START_PROMPT = f"""{BRAND_CONTEXT}

{VOICE}

You are opening a brand-new serialized dark-fantasy saga for the \
BattleFoundry blog -- one chapter a day, where each chapter introduces the \
miniature pictured as the next character or event. Write the OPENING \
chapter (3-4 short paragraphs). End on a note that demands a sequel.

{FORMAT_RULES}"""

SAGA_CONTINUE_PROMPT_TMPL = f"""{BRAND_CONTEXT}

{VOICE}

You are continuing an ongoing serialized dark-fantasy saga. Recap of the \
last chapter:

---
{{previous_summary}}
---

Write the NEXT chapter (3-4 short paragraphs), introducing the miniature \
pictured now as the next character or event. Keep continuity. End on a \
note that demands a sequel.

{FORMAT_RULES}"""

TUTORIAL_PROMPT = f"""{BRAND_CONTEXT}

{VOICE}

{SEO_KEYWORDS}

Write a short, standalone painting or 3D-printing tutorial (3-4 short \
paragraphs), using the miniature pictured as the example. Something a \
painter or printer could use today -- real technique, not fluff.

{FORMAT_RULES}"""

LORE_PROMPT = f"""{BRAND_CONTEXT}

{VOICE}

Write a short, standalone worldbuilding entry (3-4 short paragraphs) -- the \
history, culture, or myth behind the miniature pictured. Self-contained, \
not part of any ongoing story. Read like a line out of a tabletop RPG \
sourcebook, not a fantasy novel trying too hard.

{FORMAT_RULES}"""


def _call_gemini(api_key: str, prompt: str) -> str:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30,
            )
            # Retry on server-side hiccups (503, 500, 429 rate limit); fail
            # fast on client errors like a bad key (401/403) or bad request (400).
            if resp.status_code in (500, 503, 429) and attempt < MAX_RETRIES:
                delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
                print(f"[Gemini] Got {resp.status_code}, retrying in {delay}s "
                      f"(attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(delay)
                continue
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if not text:
                raise RuntimeError("Gemini returned an empty blog post")
            return text
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
                print(f"[Gemini] Request failed ({e}), retrying in {delay}s "
                      f"(attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(delay)
    # All retries exhausted.
    if last_error:
        raise last_error
    raise RuntimeError(f"Gemini failed after {MAX_RETRIES} attempts")


def _parse(raw: str, fallback_title: str = "New Free Miniature") -> dict:
    title = fallback_title
    body = raw
    if "TITLE:" in raw and "BODY:" in raw:
        title_part = raw.split("TITLE:", 1)[1].split("BODY:", 1)[0].strip()
        body_part = raw.split("BODY:", 1)[1].strip()
        if title_part:
            title = title_part
        if body_part:
            body = body_part
    return {"title": title, "body": body}


def generate_blog_post(api_key: str, kind: str, previous_summary: str = None) -> dict:
    """kind is 'saga', 'tutorial', or 'lore'. For 'saga' with no previous_summary,
    starts a new saga; with previous_summary, continues it."""
    if kind == "saga":
        if previous_summary:
            prompt = SAGA_CONTINUE_PROMPT_TMPL.format(previous_summary=previous_summary)
        else:
            prompt = SAGA_START_PROMPT
    elif kind == "tutorial":
        prompt = TUTORIAL_PROMPT
    elif kind == "lore":
        prompt = LORE_PROMPT
    else:
        raise ValueError(f"Unknown post kind: {kind}")

    raw = _call_gemini(api_key, prompt)
    return _parse(raw)
