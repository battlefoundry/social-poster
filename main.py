"""
Picks a random image from a public Google Drive folder and posts the same
caption + image to Bluesky, Mastodon, Tumblr, and Pinterest.

All secrets are read from environment variables (see .env.example).
Run manually with:  python main.py
Or let GitHub Actions run it on a schedule (see .github/workflows/daily-post.yml).
"""
import os
import sys
import traceback

from platforms import gdrive, bluesky, mastodon, tumblr, pinterest, image_utils

CAPTION = """FREE Miniatures at

Fantasy: https://cults3d.com/@BattleFoundry
Scifi: https://cults3d.com/@BATTLEFOUNDRYSCIFI
Resin Statue: https://cults3d.com/@BlacksiteSyndicate

#dnd #ttrpg #tabletopwargame #3dprinting #stl #freeminiatures"""

HASHTAGS = ["dnd", "ttrpg", "tabletopwargame", "3dprinting", "stl", "freeminiatures"]
IMAGE_ALT = "Free tabletop miniature from BattleFoundry / Blacksite Syndicate"
PINTEREST_LINK = "https://cults3d.com/@BattleFoundry"
PINTEREST_TITLE = "Free Tabletop Miniatures"


def env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def run_step(name: str, fn):
    """Run one platform's post function; log and continue on failure so one
    broken platform doesn't stop the others."""
    try:
        fn()
    except Exception:
        print(f"[{name}] FAILED:", file=sys.stderr)
        traceback.print_exc()


def main():
    folder_id = env("GDRIVE_FOLDER_ID")
    gdrive_api_key = env("GDRIVE_API_KEY")

    print("Picking a random image from Google Drive...")
    all_images = gdrive.list_images(folder_id, gdrive_api_key)
    print(f"Found {len(all_images)} eligible images in the Drive folder.")

    image = gdrive.pick_random_image(folder_id, gdrive_api_key)
    print(f"Chosen image: {image['name']}")

    compressed_bytes, compressed_mime = image_utils.compress_image(
        image["bytes"], image.get("mimeType", "image/jpeg")
    )
    image["bytes"] = compressed_bytes
    image["mimeType"] = compressed_mime

    run_step("Bluesky", lambda: bluesky.post(
        handle=env("BSKY_HANDLE"),
        app_password=env("BSKY_APP_PASSWORD"),
        text=CAPTION,
        image_bytes=image["bytes"],
        image_alt=IMAGE_ALT,
    ))

    run_step("Mastodon", lambda: mastodon.post(
        instance_url=env("MASTODON_INSTANCE_URL"),
        access_token=env("MASTODON_ACCESS_TOKEN"),
        text=CAPTION,
        image_bytes=image["bytes"],
        image_alt=IMAGE_ALT,
        mime_type=image.get("mimeType", "image/png"),
    ))

    run_step("Tumblr", lambda: tumblr.post(
        consumer_key=env("TUMBLR_CONSUMER_KEY"),
        consumer_secret=env("TUMBLR_CONSUMER_SECRET"),
        oauth_token=env("TUMBLR_OAUTH_TOKEN"),
        oauth_secret=env("TUMBLR_OAUTH_SECRET"),
        blog_name=env("TUMBLR_BLOG_NAME"),
        caption=CAPTION,
        hashtags=HASHTAGS,
        image_bytes=image["bytes"],
    ))

    if env("PINTEREST_ACCESS_TOKEN", required=False) and env("PINTEREST_BOARD_ID", required=False):
        run_step("Pinterest", lambda: pinterest.post(
            access_token=env("PINTEREST_ACCESS_TOKEN"),
            board_id=env("PINTEREST_BOARD_ID"),
            title=PINTEREST_TITLE,
            description=CAPTION,
            link=PINTEREST_LINK,
            image_public_url=image["public_view_url"],
        ))
    else:
        print("[Pinterest] Skipped (no credentials set yet).")

    print("Done.")


if __name__ == "__main__":
    main()
