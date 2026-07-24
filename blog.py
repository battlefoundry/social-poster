"""
Generates one new blog post a day: picks a random image from the Google
Drive folder, writes a blog-style writeup with Gemini, saves everything as
a static HTML page under docs/, and updates the blog's homepage listing.

GitHub Pages serves the docs/ folder directly -- see README for one-time
setup (Settings -> Pages -> Deploy from branch -> main -> /docs).

Run manually with:  python blog.py
Or let GitHub Actions run it on a schedule (see .github/workflows/daily-blog.yml).
"""
import datetime
import html
import json
import os
import re
import sys
import traceback
import uuid

from platforms import gdrive, image_utils, blog_gen

DOCS_DIR = "docs"
POSTS_DIR = os.path.join(DOCS_DIR, "posts")
IMAGES_DIR = os.path.join(DOCS_DIR, "assets", "images")
DATA_FILE = os.path.join(DOCS_DIR, "posts_data.json")

STORE_LINKS = [
    ("Fantasy", "https://cults3d.com/@BattleFoundry"),
    ("Scifi", "https://cults3d.com/@BATTLEFOUNDRYSCIFI"),
    ("Grimdark", "https://cults3d.com/@DREADWORKS"),
    ("Resin Statue", "https://cults3d.com/@BlacksiteSyndicate"),
]

SITE_TITLE = "BattleFoundry Blog"


def env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:50] or "post"


def load_posts() -> list:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posts(posts: list):
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)


POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - {site_title}</title>
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<header class="site-header">
  <a href="../index.html" class="site-title">{site_title}</a>
</header>
<main class="post">
  <h1>{title}</h1>
  <p class="post-date">{date}</p>
  <img class="post-image" src="../assets/images/{image_file}" alt="{title}">
  <div class="post-body">
{body_html}
  </div>
  <div class="store-links">
    <h3>Get free miniatures:</h3>
    <ul>
{links_html}
    </ul>
  </div>
  <a class="back-link" href="../index.html">&larr; Back to all posts</a>
</main>
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{site_title}</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-header">
  <span class="site-title">{site_title}</span>
  <p class="site-subtitle">Free tabletop miniatures &amp; resin statues</p>
</header>
<main class="post-list">
{cards_html}
</main>
</body>
</html>
"""

CARD_TEMPLATE = """  <a class="post-card" href="posts/{slug}.html">
    <img src="assets/images/{image_file}" alt="{title}">
    <div class="post-card-body">
      <h2>{title}</h2>
      <p class="post-date">{date}</p>
      <p class="post-excerpt">{excerpt}</p>
    </div>
  </a>
"""


def render_body_html(body: str) -> str:
    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    return "\n".join(f"    <p>{html.escape(p)}</p>" for p in paragraphs)


def main():
    folder_id = env("GDRIVE_FOLDER_ID")
    gdrive_api_key = env("GDRIVE_API_KEY")
    gemini_key = env("GEMINI_API_KEY")

    print("Picking a random image from Google Drive...")
    image = gdrive.pick_random_image(folder_id, gdrive_api_key)
    print(f"Chosen image: {image['name']}")

    compressed_bytes, compressed_mime = image_utils.compress_image(
        image["bytes"], image.get("mimeType", "image/jpeg")
    )

    print("Writing blog post with Gemini...")
    post = blog_gen.generate_blog_post(gemini_key)
    title = post["title"]
    body = post["body"]
    print(f"Title: {title}")

    slug = slugify(title) + "-" + uuid.uuid4().hex[:6]
    image_file = f"{slug}.jpg"
    date_str = datetime.date.today().strftime("%B %d, %Y")

    os.makedirs(POSTS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    with open(os.path.join(IMAGES_DIR, image_file), "wb") as f:
        f.write(compressed_bytes)

    links_html = "\n".join(
        f'      <li><strong>{name}:</strong> <a href="{url}">{url}</a></li>'
        for name, url in STORE_LINKS
    )

    post_html = POST_TEMPLATE.format(
        title=html.escape(title),
        site_title=SITE_TITLE,
        date=date_str,
        image_file=image_file,
        body_html=render_body_html(body),
        links_html=links_html,
    )
    with open(os.path.join(POSTS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(post_html)

    posts = load_posts()
    excerpt = body.split("\n")[0].strip()
    if len(excerpt) > 140:
        excerpt = excerpt[:140].rsplit(" ", 1)[0] + "…"
    posts.insert(0, {
        "slug": slug,
        "title": title,
        "date": date_str,
        "image_file": image_file,
        "excerpt": excerpt,
    })
    save_posts(posts)

    cards_html = "\n".join(
        CARD_TEMPLATE.format(
            slug=p["slug"],
            image_file=p["image_file"],
            title=html.escape(p["title"]),
            date=p["date"],
            excerpt=html.escape(p["excerpt"]),
        )
        for p in posts
    )
    index_html = INDEX_TEMPLATE.format(site_title=SITE_TITLE, cards_html=cards_html)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"Published new post: {slug}")
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
