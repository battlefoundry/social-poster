# BattleFoundry Social Poster

Picks a random image from a public Google Drive folder and posts the same
caption + image to **Bluesky, Mastodon, Tumblr, and Pinterest**, once a day,
for free, using GitHub Actions.

Everything below is done in a web browser — no phone or mobile app needed.

---

## 1. Put your images in Google Drive

1. Create a folder in Google Drive, upload your promo images into it.
2. Right-click the folder → **Share** → change access to **"Anyone with the link" → Viewer**.
3. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/`**`THIS_PART`**

## 2. Get a Google Drive API key

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) → create a project (any name).
2. Go to **APIs & Services → Library**, search "Google Drive API", click **Enable**.
3. Go to **APIs & Services → Credentials → Create Credentials → API key**.
4. Copy the key. (Optional but recommended: click "Restrict key" → restrict it to the Google Drive API only.)

→ `GDRIVE_FOLDER_ID` and `GDRIVE_API_KEY`

## 3. Bluesky

1. In the Bluesky app/site: **Settings → App Passwords → Add App Password**.
2. Name it anything (e.g. "poster-bot"), copy the generated password.

→ `BSKY_HANDLE` (e.g. `battlefoundry.bsky.social`), `BSKY_APP_PASSWORD`

## 4. Mastodon

1. On your Mastodon instance: **Preferences → Development → New Application**.
2. Name it anything, check the `write:media` and `write:statuses` scopes.
3. Click **Submit**, then open the application and copy the **access token**.

→ `MASTODON_INSTANCE_URL` (e.g. `https://mastodon.social`), `MASTODON_ACCESS_TOKEN`

## 5. Tumblr

1. Go to [tumblr.com/oauth/apps](https://www.tumblr.com/oauth/apps) → **Register application**.
2. Fill in any name/description/URL, submit. Copy the **OAuth Consumer Key** and **Secret**.
3. Use Tumblr's [interactive console](https://api.tumblr.com/console) (or the `pytumblr` library's helper) to
   generate an **OAuth Token** and **OAuth Token Secret** for your account — click "Sign in", it walks you
   through it in the browser.

→ `TUMBLR_CONSUMER_KEY`, `TUMBLR_CONSUMER_SECRET`, `TUMBLR_OAUTH_TOKEN`, `TUMBLR_OAUTH_SECRET`,
  `TUMBLR_BLOG_NAME` (your blog's short name, e.g. `battlefoundry` from `battlefoundry.tumblr.com`)

## 6. Pinterest

1. Go to [developers.pinterest.com/apps](https://developers.pinterest.com/apps/) → **Create app**.
2. Once created, use the **"Generate access token"** flow in the app dashboard (it walks you through
   authorizing your own Pinterest account in the browser) — request the `pins:write` and `boards:read` scopes.
3. Create (or pick an existing) board on Pinterest, get its **board ID** from the board's URL or via a
   `GET /v5/boards` API call.

→ `PINTEREST_ACCESS_TOKEN`, `PINTEREST_BOARD_ID`

---

## 7. Put it all on GitHub and schedule it

1. Create a new **private** GitHub repo, push this folder to it.
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**, and add every
   variable listed above (same names, e.g. `GDRIVE_FOLDER_ID`, `BSKY_HANDLE`, etc.) one by one.
3. That's it — `.github/workflows/daily-post.yml` runs automatically every day at 15:00 UTC.
   Edit the `cron:` line in that file to change the time (cron is always in UTC).
4. To test it immediately without waiting: go to the repo's **Actions** tab → **Daily Social Post** →
   **Run workflow**.

## Testing locally first (optional but recommended)

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in your real values
export $(cat .env | xargs)  # loads them into your shell (macOS/Linux)
python main.py
```

## Notes

- If one platform's post fails (bad token, rate limit, etc.), the script logs the error and still
  posts to the others — one broken credential won't block everything.
- The caption text and hashtags live at the top of `main.py` — edit `CAPTION` there any time you want
  to change the wording.
- Adding Threads, Instagram, or Facebook later: Meta's app review takes a few weeks, but once approved,
  add a new `platforms/threads.py` module following the same pattern as the others and call it from `main.py`.
