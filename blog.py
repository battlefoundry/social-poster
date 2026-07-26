"""
Generates one new blog post a day: picks a random image from the Google
Drive folder, writes content with Gemini (rotating between an ongoing saga,
standalone tutorials, and standalone lore), saves it as a static HTML page,
and rebuilds three things every run:
  - docs/index.html   the landing page (hero + featured + story teaser)
  - docs/blog.html     the full post listing
  - docs/sitemap.xml / robots.txt   SEO files

GitHub Pages serves the docs/ folder directly -- see README for one-time
setup (Settings -> Pages -> Deploy from branch -> main -> /docs).

Run manually with:  python blog.py
Or let GitHub Actions run it on a schedule (see .github/workflows/daily-blog.yml).
"""
import datetime
import html
import json
import os
import random
import re
import sys
import traceback
import uuid

from platforms import gdrive, image_utils, blog_gen

DOCS_DIR = "docs"
POSTS_DIR = os.path.join(DOCS_DIR, "posts")
IMAGES_DIR = os.path.join(DOCS_DIR, "assets", "images")
DATA_FILE = os.path.join(DOCS_DIR, "posts_data.json")

# NOTE: update this if the repo or GitHub Pages URL ever changes.
SITE_URL = "https://battlefoundry.github.io/social-poster"

STORE_LINKS = [
    ("Fantasy", "https://cults3d.com/@BattleFoundry"),
    ("Scifi", "https://cults3d.com/@BATTLEFOUNDRYSCIFI"),
    ("Grimdark", "https://cults3d.com/@DREADWORKS"),
    ("Resin Statue", "https://cults3d.com/@BlacksiteSyndicate"),
]

SITE_TITLE = "BattleFoundry"
SITE_TAGLINE = "Free D&D and tabletop wargaming miniature STLs"

POST_TYPES = ["saga", "tutorial", "lore"]
TYPE_LABELS = {"saga": "Chronicle", "tutorial": "Workshop", "lore": "Lore"}


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


def meta_description(text: str, limit: int = 155) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google-site-verification" content="dz-Zek-RNWoTrZl_QB-0ewj0SuxY1V4u0t3tJrb2kAo" />
<title>{title} - {site_title}</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical_url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:image" content="{image_url}">
<meta property="og:url" content="{canonical_url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{meta_desc}">
<meta name="twitter:image" content="{image_url}">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<nav class="site-nav">
  <a href="../index.html" class="logo"><img src="../assets/logo.png" alt="{site_title}"><span class="logo-text">{site_title}</span></a>
  <div class="links"><a href="../blog.html">Chronicle</a></div>
</nav>
<main class="post">
  <span class="post-type">{type_label}</span>
  <h1>{title}</h1>
  <p class="post-date">{date}</p>
  <img class="post-image" src="../assets/images/{image_file}" alt="{image_alt}">
  <div class="post-body">
{body_html}
  </div>
  <div class="store-links">
    <h3>Get free miniatures:</h3>
    <ul>
{links_html}
    </ul>
  </div>
  <a class="back-link" href="../blog.html">&larr; BACK TO ALL POSTS</a>
</main>
</body>
</html>
"""

BLOG_LIST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google-site-verification" content="dz-Zek-RNWoTrZl_QB-0ewj0SuxY1V4u0t3tJrb2kAo" />
<title>The Chronicle - {site_title}</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{site_url}/blog.html">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<nav class="site-nav">
  <a href="index.html" class="logo"><img src="assets/logo.png" alt="{site_title}"><span class="logo-text">{site_title}</span></a>
  <div class="links"><a href="blog.html">Chronicle</a></div>
</nav>
<header class="site-header">
  <span class="site-title">The Chronicle</span>
  <p class="site-subtitle">Stories, tips, and lore from the forge</p>
</header>
<main class="post-list">
{cards_html}
</main>
</body>
</html>
"""

CARD_TEMPLATE = """  <a class="post-card" href="posts/{slug}.html">
    <img src="assets/images/{image_file}" alt="{image_alt}">
    <div class="post-card-body">
      <span class="post-type">{type_label}</span>
      <h2>{title}</h2>
      <p class="post-date">{date}</p>
      <p class="post-excerpt">{excerpt}</p>
    </div>
  </a>
"""

FEATURED_CARD_TEMPLATE = """    <a class="post-card" href="posts/{slug}.html">
      <img src="assets/images/{image_file}" alt="{image_alt}">
      <div class="post-card-body">
        <span class="post-type">{type_label}</span>
        <h2>{title}</h2>
        <p class="post-excerpt">{excerpt}</p>
      </div>
    </a>
"""

LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google-site-verification" content="dz-Zek-RNWoTrZl_QB-0ewj0SuxY1V4u0t3tJrb2kAo" />
<title>{site_title} — {tagline}</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{site_url}/">
<meta property="og:type" content="website">
<meta property="og:title" content="{site_title} — {tagline}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:image" content="{hero_image_url}">
<meta property="og:url" content="{site_url}/">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<nav class="site-nav">
  <a href="index.html" class="logo"><img src="assets/logo.png" alt="{site_title}"><span class="logo-text">{site_title}</span></a>
  <div class="links"><a href="blog.html">Chronicle</a></div>
</nav>

<section class="hero">
  <div class="hero-copy">
    <span class="mono-tag">FREE STL DROP — DAILY</span>
    <h1>Arm your table.<br>For free.</h1>
    <p>Fantasy, sci-fi, and grimdark miniatures for D&amp;D and tabletop wargaming. New free STLs, every single day.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="https://cults3d.com/@BattleFoundry">Browse the Vault</a>
      <a class="btn btn-secondary" href="blog.html">Read the Chronicle</a>
    </div>
  </div>
  <div class="hero-image-wrap">
    <img src="assets/images/{hero_image_file}" alt="{hero_image_alt}">
  </div>
</section>

<section class="section">
  <div class="section-head">
    <span class="mono-tag">Latest Casts</span>
    <h2>Fresh off the forge</h2>
  </div>
  <div class="featured-grid">
{featured_html}
  </div>
</section>

<section class="section">
  <div class="section-head">
    <span class="mono-tag">The Chronicle</span>
    <h2>The story so far</h2>
  </div>
  <div class="story-teaser">
    <img src="assets/images/{story_image_file}" alt="{story_image_alt}">
    <div class="story-teaser-body">
      <h3>{story_title}</h3>
      <p>{story_excerpt}</p>
      <a class="btn btn-secondary" href="posts/{story_slug}.html">Continue reading</a>
    </div>
  </div>
</section>

<footer class="footer-links">
  <div class="store-list">
{store_links_html}
  </div>
  <p class="fine-print">All miniatures free to download and print. New releases daily.</p>
</footer>
</body>
</html>
"""

SITEMAP_URL_TMPL = """  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
  </url>
"""


def render_body_html(body: str) -> str:
    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    return "\n".join(f"    <p>{html.escape(p)}</p>" for p in paragraphs)


def write_seo_files(posts: list):
    """robots.txt (static) and sitemap.xml (rebuilt from current posts)."""
    robots_path = os.path.join(DOCS_DIR, "robots.txt")
    if not os.path.exists(robots_path):
        with open(robots_path, "w", encoding="utf-8") as f:
            f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    today = datetime.date.today().isoformat()
    urls = [
        SITEMAP_URL_TMPL.format(loc=f"{SITE_URL}/", lastmod=today),
        SITEMAP_URL_TMPL.format(loc=f"{SITE_URL}/blog.html", lastmod=today),
    ]
    for p in posts:
        urls.append(SITEMAP_URL_TMPL.format(
            loc=f"{SITE_URL}/posts/{p['slug']}.html", lastmod=today
        ))
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(urls) +
        "</urlset>\n"
    )
    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)


def build_blog_list(posts: list):
    cards_html = "\n".join(
        CARD_TEMPLATE.format(
            slug=p["slug"],
            image_file=p["image_file"],
            image_alt=html.escape(p.get("image_alt", p["title"])),
            title=html.escape(p["title"]),
            date=p["date"],
            excerpt=html.escape(p["excerpt"]),
            type_label=p.get("type_label", "Chronicle"),
        )
        for p in posts
    )
    meta_desc = (
        "Stories, painting tutorials, and lore from BattleFoundry — free "
        "D&D and tabletop wargaming miniature STLs, updated daily."
    )
    blog_html = BLOG_LIST_TEMPLATE.format(
        site_title=SITE_TITLE,
        cards_html=cards_html or '  <p style="color:var(--ink-dim);">No posts yet.</p>',
        meta_desc=html.escape(meta_desc),
        site_url=SITE_URL,
    )
    with open(os.path.join(DOCS_DIR, "blog.html"), "w", encoding="utf-8") as f:
        f.write(blog_html)


def build_landing_page(posts: list):
    if not posts:
        return  # nothing to feature yet

    hero_post = posts[0]
    featured = posts[:3]
    story_post = next((p for p in posts if p.get("type") == "saga"), posts[0])

    featured_html = "\n".join(
        FEATURED_CARD_TEMPLATE.format(
            slug=p["slug"],
            image_file=p["image_file"],
            image_alt=html.escape(p.get("image_alt", p["title"])),
            title=html.escape(p["title"]),
            excerpt=html.escape(p["excerpt"]),
            type_label=p.get("type_label", "Chronicle"),
        )
        for p in featured
    )

    store_links_html = "\n".join(
        f'    <a href="{url}">{name}</a>' for name, url in STORE_LINKS
    )

    meta_desc = (
        "Free D&D and tabletop wargaming miniature STLs — fantasy, sci-fi, "
        "grimdark, and resin statues. New free miniatures forged daily."
    )

    landing_html = LANDING_TEMPLATE.format(
        site_title=SITE_TITLE,
        tagline=SITE_TAGLINE,
        meta_desc=html.escape(meta_desc),
        site_url=SITE_URL,
        hero_image_file=hero_post["image_file"],
        hero_image_alt=html.escape(hero_post.get("image_alt", hero_post["title"])),
        hero_image_url=f"{SITE_URL}/assets/images/{hero_post['image_file']}",
        featured_html=featured_html,
        story_image_file=story_post["image_file"],
        story_image_alt=html.escape(story_post.get("image_alt", story_post["title"])),
        story_title=html.escape(story_post["title"]),
        story_excerpt=html.escape(story_post["excerpt"]),
        story_slug=story_post["slug"],
        store_links_html=store_links_html,
    )
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(landing_html)


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

    posts = load_posts()

    kind = random.choice(POST_TYPES)
    print(f"Chosen post type: {kind}")

    previous_summary = None
    if kind == "saga":
        last_saga = next((p for p in posts if p.get("type") == "saga"), None)
        if last_saga:
            previous_summary = last_saga.get("story_context", "")

    print("Writing blog post with Gemini...")
    post = blog_gen.generate_blog_post(gemini_key, kind, previous_summary)
    title = post["title"]
    body = post["body"]
    print(f"Title: {title}")

    slug = slugify(title) + "-" + uuid.uuid4().hex[:6]
    image_file = f"{slug}.jpg"
    date_str = datetime.date.today().strftime("%B %d, %Y")
    type_label = TYPE_LABELS[kind]
    image_alt = f"{title} — free {type_label.lower()} miniature STL for D&D and tabletop wargaming"

    os.makedirs(POSTS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    with open(os.path.join(IMAGES_DIR, image_file), "wb") as f:
        f.write(compressed_bytes)

    links_html = "\n".join(
        f'      <li><strong>{name}:</strong> <a href="{url}">{url}</a></li>'
        for name, url in STORE_LINKS
    )

    excerpt_full = body.split("\n")[0].strip()
    meta_desc = meta_description(excerpt_full)
    canonical_url = f"{SITE_URL}/posts/{slug}.html"
    image_url = f"{SITE_URL}/assets/images/{image_file}"

    post_html = POST_TEMPLATE.format(
        title=html.escape(title),
        site_title=SITE_TITLE,
        type_label=type_label,
        date=date_str,
        image_file=image_file,
        image_alt=html.escape(image_alt),
        body_html=render_body_html(body),
        links_html=links_html,
        meta_desc=html.escape(meta_desc),
        canonical_url=canonical_url,
        image_url=image_url,
    )
    with open(os.path.join(POSTS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(post_html)

    excerpt = excerpt_full
    if len(excerpt) > 140:
        excerpt = excerpt[:140].rsplit(" ", 1)[0] + "…"

    entry = {
        "slug": slug,
        "title": title,
        "date": date_str,
        "image_file": image_file,
        "image_alt": image_alt,
        "excerpt": excerpt,
        "type": kind,
        "type_label": type_label,
    }
    if kind == "saga":
        # Keep the full body as context for the next chapter.
        entry["story_context"] = body

    posts.insert(0, entry)
    save_posts(posts)

    build_blog_list(posts)
    build_landing_page(posts)
    write_seo_files(posts)

    print(f"Published new post: {slug} ({kind})")
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
