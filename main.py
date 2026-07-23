"""
Picks a random image from a public Google Drive folder and a random caption
variant, then posts both to Bluesky and Mastodon (and Pinterest, once set up).

All secrets are read from environment variables (see .env.example).
Run manually with:  python main.py
Or let GitHub Actions run it on a schedule (see .github/workflows/daily-post.yml).
"""
import os
import random
import sys
import traceback

from platforms import gdrive, bluesky, mastodon, pinterest, image_utils, caption_gen

# Several worded-differently variants of the same core message. One is picked
# at random each run so repeated daily posts don't look like copy-pasted spam.
CAPTIONS = [
"""FREE Miniatures at

Fantasy: https://cults3d.com/@BattleFoundry
Scifi: https://cults3d.com/@BATTLEFOUNDRYSCIFI
Grimdark: https://cults3d.com/@DREADWORKS
Resin Statue: https://cults3d.com/@BlacksiteSyndicate

#dnd #ttrpg #tabletopwargame #3dprinting #stl #freeminiatures""",

"""Free STLs, no catch. Grab your next miniature here:

Fantasy: https://cults3d.com/@BattleFoundry
Scifi: https://cults3d.com/@BATTLEFOUNDRYSCIFI
Grimdark: https://cults3d.com/@DREADWORKS
Resin Statue: https://cults3d.com/@BlacksiteSyndicate

#stl #3dprinting #dnd #ttrpg #freeminiatures""",

"""Stock up your tabletop for $0. New free minis waiting for you:

Fantasy: https://cults3d.com/@BattleFoundry
Scifi: https://cults3d.com/@BATTLEFOUNDRYSCIFI
Grimdark: https://cults3d.com/@DREADWORKS
Resin Statue: https://cults3d.com/@BlacksiteSyndicate

#tabletopwargame #dnd #ttrpg #3dprinting #freeminiatures""",

"""Printing tonight? Here's a free one for the pile:

Fantasy: https://cults3d.com/@BattleFoundry
Scifi: https://cults3d.com/@BATTLEFOUNDRYSCIFI
Grimdark: https://cults3d.com/@DREADWORKS
Resin Statue: https://cults3d.com/@BlacksiteSyndicate

#3dprinting #stl #ttrpg #dnd #freeminiatures""",

"""No cost, no strings — free miniature STLs for your table:

Fantasy: https://cults3d.com/@BattleFoundry
Scifi: https://cults3d.com/@BATTLEFOUNDRYSCIFI
Grimdark: https://cults3d.com/@DREADWORKS
Resin Statue: https://cults3d.com/@BlacksiteSyndicate

#freeminiatures #dnd #ttrpg #3dprinting #tabletopwargame""",
]

# Engagement-style posts — questions, tips, community prompts. No links, just
# something people actually want to reply to. Mixed into the rotation below
# so the feed isn't 100% "buy my stuff."
ENGAGEMENT_CAPTIONS = [
"""Fantasy or Sci-fi tonight — which are you printing? 👇

#3dprinting #dnd #ttrpg #tabletopwargame""",

"""Resin or FDM for minis? Pick a side. 👇

#3dprinting #stl #miniatures #ttrpg""",

"""What's still sitting unpainted in your queue right now? Be honest. 😅

#dnd #ttrpg #tabletopwargame #miniaturepainting""",

"""Printing tip: cutting your supports down before removing them fully makes
cleanup way faster and reduces breakage on thin details.

#3dprinting #stl #resinprinting""",

"""Tag someone who needs free minis for their next campaign. 👇

#dnd #ttrpg #tabletopwargame #freeminiatures""",

"""What's the most ambitious mini you've ever attempted to paint?

#miniaturepainting #dnd #ttrpg #tabletopwargame""",
]

# Weighted mix: most posts are promo, some are engagement-only.
PROMO_WEIGHT = 3
ENGAGEMENT_WEIGHT = 1

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

    caption_pool = random.choices(
        [CAPTIONS, ENGAGEMENT_CAPTIONS],
        weights=[PROMO_WEIGHT, ENGAGEMENT_WEIGHT],
        k=1,
    )[0]
    kind = "promo" if caption_pool is CAPTIONS else "engagement"

    gemini_key = env("GEMINI_API_KEY", required=False)
    caption = None
    if gemini_key:
        try:
            caption = caption_gen.generate_caption(gemini_key, kind)
            print(f"Chosen caption type: {kind} (AI-generated via Gemini)")
        except Exception:
            print("[Gemini] Caption generation failed, falling back to static list:", file=sys.stderr)
            traceback.print_exc()
    if not caption:
        caption = random.choice(caption_pool)
        print(f"Chosen caption type: {kind} (static fallback)")

    compressed_bytes, compressed_mime = image_utils.compress_image(
        image["bytes"], image.get("mimeType", "image/jpeg")
    )
    image["bytes"] = compressed_bytes
    image["mimeType"] = compressed_mime

    run_step("Bluesky", lambda: bluesky.post(
        handle=env("BSKY_HANDLE"),
        app_password=env("BSKY_APP_PASSWORD"),
        text=caption,
        image_bytes=image["bytes"],
        image_alt=IMAGE_ALT,
    ))

    run_step("Mastodon", lambda: mastodon.post(
        instance_url=env("MASTODON_INSTANCE_URL"),
        access_token=env("MASTODON_ACCESS_TOKEN"),
        text=caption,
        image_bytes=image["bytes"],
        image_alt=IMAGE_ALT,
        mime_type=image.get("mimeType", "image/png"),
    ))

    if env("PINTEREST_ACCESS_TOKEN", required=False) and env("PINTEREST_BOARD_ID", required=False):
        run_step("Pinterest", lambda: pinterest.post(
            access_token=env("PINTEREST_ACCESS_TOKEN"),
            board_id=env("PINTEREST_BOARD_ID"),
            title=PINTEREST_TITLE,
            description=caption,
            link=PINTEREST_LINK,
            image_public_url=image["public_view_url"],
        ))
    else:
        print("[Pinterest] Skipped (no credentials set yet).")

    print("Done.")


if __name__ == "__main__":
    main()
