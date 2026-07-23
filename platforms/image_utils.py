"""Shrinks an image (if needed) so it fits under Bluesky's ~2MB upload limit."""
import io
from PIL import Image

MAX_BYTES = 1_900_000  # a bit under Bluesky's ~2,000,000-byte limit, for safety


def compress_image(image_bytes: bytes, mime_type: str = "image/jpeg"):
    """Returns (bytes, mime_type). If already small enough, returns unchanged."""
    if len(image_bytes) <= MAX_BYTES:
        return image_bytes, mime_type

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    quality = 90
    width, height = img.size

    while True:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= MAX_BYTES:
            return data, "image/jpeg"
        if quality > 40:
            quality -= 10
        else:
            width = int(width * 0.85)
            height = int(height * 0.85)
            img = img.resize((width, height), Image.LANCZOS)
            quality = 75
