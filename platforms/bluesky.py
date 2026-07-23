"""Post text + an image to Bluesky using an app password."""
import re
from atproto import Client, client_utils


def post(handle: str, app_password: str, text: str, image_bytes: bytes, image_alt: str):
    client = Client()
    client.login(handle, app_password)

    tb = client_utils.TextBuilder()
    # Split into words and whitespace (including newlines) as separate tokens,
    # so URLs/hashtags never accidentally swallow surrounding text.
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
