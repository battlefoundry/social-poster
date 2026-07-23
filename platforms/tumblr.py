"""Post a photo to Tumblr using OAuth1 credentials (pytumblr)."""
import base64
import pytumblr


def post(consumer_key: str, consumer_secret: str, oauth_token: str,
          oauth_secret: str, blog_name: str, caption: str,
          hashtags: list[str], image_bytes: bytes):
    client = pytumblr.TumblrRestClient(
        consumer_key, consumer_secret, oauth_token, oauth_secret
    )

    client.create_photo(
        blog_name,
        state="published",
        caption=caption,
        tags=hashtags,
        data64=base64.b64encode(image_bytes).decode("utf-8"),
    )
    print("[Tumblr] Posted.")
