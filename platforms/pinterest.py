"""Create a Pin on Pinterest using the Pinterest API v5."""
import requests

PINTEREST_API = "https://api.pinterest.com/v5/pins"


def post(access_token: str, board_id: str, title: str, description: str,
          link: str, image_public_url: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "board_id": board_id,
        "title": title,
        "description": description,
        "link": link,
        "media_source": {
            "source_type": "image_url",
            "url": image_public_url,
        },
    }
    resp = requests.post(PINTEREST_API, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    print("[Pinterest] Posted.")
