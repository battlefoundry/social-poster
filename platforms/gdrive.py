"""
Pulls the list of images from a PUBLIC Google Drive folder and downloads
a random one. Uses a simple Google API key (no OAuth) — this only works
because the folder is shared as "Anyone with the link can view".
"""
import random
import requests

DRIVE_LIST_URL = "https://www.googleapis.com/drive/v3/files"
IMAGE_MIME_PREFIX = "image/"


def list_images(folder_id: str, api_key: str) -> list[dict]:
    """Return a list of {id, name, mimeType} for every image in the folder."""
    params = {
        "q": f"'{folder_id}' in parents and trashed = false",
        "key": api_key,
        "fields": "files(id, name, mimeType)",
        "pageSize": 1000,
    }
    files = []
    while True:
        resp = requests.get(DRIVE_LIST_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        params["pageToken"] = page_token

    images = [f for f in files if f.get("mimeType", "").startswith(IMAGE_MIME_PREFIX)]
    if not images:
        raise RuntimeError(
            "No images found in the Drive folder. Check the folder ID and "
            "that it's shared as 'Anyone with the link can view'."
        )
    return images


def pick_random_image(folder_id: str, api_key: str) -> dict:
    """Pick one random image and return its metadata + downloadable bytes."""
    images = list_images(folder_id, api_key)
    chosen = random.choice(images)

    download_url = f"{DRIVE_LIST_URL}/{chosen['id']}"
    resp = requests.get(
        download_url,
        params={"alt": "media", "key": api_key},
        timeout=60,
    )
    resp.raise_for_status()

    chosen["bytes"] = resp.content
    chosen["public_view_url"] = (
        f"https://drive.google.com/uc?export=view&id={chosen['id']}"
    )
    return chosen
