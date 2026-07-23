"""Post text + an image to Bluesky using an app password."""
from atproto import Client, client_utils


def post(handle: str, app_password: str, text: str, image_bytes: bytes, image_alt: str):
    client = Client()
    client.login(handle, app_password)

    tb = client_utils.TextBuilder()
    # Auto-link any http(s) URLs and #hashtags in the caption.
    for token in text.split(" "):
        stripped = token.rstrip("\n")
        if stripped.startswith("http://") or stripped.startswith("https://"):
            tb.link(stripped + " ", stripped)
        elif stripped.startswith("#") and len(stripped) > 1:
            tb.tag(stripped + " ", stripped[1:])
        else:
            tb.text(token + " ")

    client.send_image(
        text=tb,
        image=image_bytes,
        image_alt=image_alt,
    )
    print("[Bluesky] Posted.")
