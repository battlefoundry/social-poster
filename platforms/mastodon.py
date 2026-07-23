"""Post text + an image to Mastodon using an access token."""
from mastodon import Mastodon


def post(instance_url: str, access_token: str, text: str, image_bytes: bytes,
          image_alt: str, mime_type: str = "image/png"):
    m = Mastodon(access_token=access_token, api_base_url=instance_url)

    media = m.media_post(
        image_bytes,
        mime_type=mime_type,
        description=image_alt,
    )
    m.status_post(text, media_ids=[media["id"]])
    print("[Mastodon] Posted.")
