"""Post text + an image to Bluesky using an app password."""
import re
from atproto import Client, client_utils

BSKY_LIMIT = 300


def _fit_to_limit(text: str, limit: int = BSKY_LIMIT) -> str:
    """If text is too long for Bluesky, trim trailing hashtags (one at a
    time) until it fits. Falls back to a hard truncation if still too long."""
    if len(text) <= limit:
        return text

    lines = text.split("\n")
    if lines and lines[-1].strip().startswith("#"):
        tags = lines[-1].split()
        while tags and len("\n".join(lines[:-1] + [" ".join(tags)])) > limit:
            tags.pop()
        lines[-1] = " ".join(tags)
        trimmed = "\n".join(lines).rstrip()
        if len(trimmed) <= limit:
            return trimmed

    # Still too long (e.g. links alone exceed the limit) -- hard truncate.
    return text[: limit - 1].rstrip() + "…"


def post(handle: str, app_password: str, text: str, image_bytes: bytes, image_alt: str):
    text = _fit_to_limit(text)

    client = Client()
    client.login(handle, app_password)

    tb = client_utils.TextBuilder()
    tokens = re.split(r'(\s+)', text)

    for token in tokens:
        if token == "":
            continue
        if token.isspace():
            tb.text(token)
        elif token.startswith("http://") or token.startswith("https://"):
            tb.link(token, token)
        elif token.startswith("#") and len(token) > 1:
            tb.tag(token, token[1:])
        else:
            tb.text(token)

    client.send_image(
        text=tb,
        image=image_bytes,
        image_alt=image_alt,
    )
    print("[Bluesky] Posted.")
