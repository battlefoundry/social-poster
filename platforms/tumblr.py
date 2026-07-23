"""Post a photo to Tumblr using OAuth1 credentials (pytumblr)."""
import os
import tempfile
import pytumblr


def post(consumer_key: str, consumer_secret: str, oauth_token: str,
          oauth_secret: str, blog_name: str, caption: str,
          hashtags: list[str], image_bytes: bytes):
    client = pytumblr.TumblrRestClient(
        consumer_key, consumer_secret, oauth_token, oauth_secret
    )

    # pytumblr's create_photo expects a file PATH for 'data', not raw bytes,
    # so we write to a temp file first.
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        response = client.create_photo(
            blog_name,
            state="published",
            caption=caption,
            tags=hashtags,
            data=tmp_path,
        )
    finally:
        os.remove(tmp_path)

    print(f"[Tumblr] API response: {response}")
    if isinstance(response, dict) and response.get("meta", {}).get("status", 200) >= 300:
        raise RuntimeError(f"Tumblr API returned an error: {response}")
    if isinstance(response, dict) and "errors" in response:
        raise RuntimeError(f"Tumblr API returned an error: {response}")

    print("[Tumblr] Posted.")
