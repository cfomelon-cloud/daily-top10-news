# Daily Top 10 — UK · Hong Kong · Singapore · US

A self-updating news site. Twice a day, GitHub's servers ask the Claude API
(with live web search) to compile the top 10 stories in each of four
jurisdictions, then rebuild `index.html`. GitHub Pages serves it as a public
web page. No server of your own, no manual steps after setup.

```
GitHub Actions (cron, twice daily)
        │
        ▼
   update_news.py ──► Claude API + web search ──► regenerates index.html
        │
        ▼
   git commit + push  ──►  GitHub Pages serves your live site
```

---

## What's in this repo

| File | What it does |
|---|---|
| `index.html` | The web page itself (regenerated on every run). |
| `update_news.py` | Fetches the news and rebuilds `index.html`. |
| `.github/workflows/update.yml` | The schedule + the steps GitHub runs. |
| `requirements.txt` | The one Python package needed (`anthropic`). |

---

## One-time setup (about 15 minutes)

You do this once. After that it runs itself.

### 1. Create the repository
1. Sign in at **github.com** (create a free account if you don't have one).
2. Click **+** (top right) → **New repository**.
3. Name it e.g. `daily-top10-news`. Set it to **Public** (required for free GitHub Pages).
4. Click **Create repository**.

### 2. Upload these files
On the new repo's page, click **Add file → Upload files**, then drag in
**all the files from this folder, keeping the `.github/workflows/` folder
structure intact**. The easiest way is to drag the whole extracted folder's
contents. Then click **Commit changes**.

> If the drag-and-drop misses the hidden `.github` folder, create the
> workflow manually: **Add file → Create new file**, type the filename
> `.github/workflows/update.yml` (GitHub creates the folders as you type the
> slashes), paste the contents, and commit.

### 3. Get a Claude API key
1. Go to **console.anthropic.com** and sign in.
2. Add a payment method under **Billing** (usage is billed per run — see cost note below).
3. Under **API Keys**, click **Create Key**, and copy it (starts with `sk-ant-`).

### 4. Give the key to GitHub (as a secret, never in the code)
1. In your repo: **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `ANTHROPIC_API_KEY`  ·  Secret: paste your `sk-ant-...` key  ·  **Add secret**.

### 5. Let the workflow write back to the repo
1. **Settings → Actions → General**.
2. Scroll to **Workflow permissions** → select **Read and write permissions** → **Save**.

### 6. Turn on GitHub Pages
1. **Settings → Pages**.
2. Under **Source**, choose **Deploy from a branch**.
3. Branch: **main**, folder: **/ (root)** → **Save**.
4. After a minute, this page shows your live URL, e.g.
   `https://<your-username>.github.io/daily-top10-news/`.

### 7. Do a test run
1. Go to the **Actions** tab → select **Update news site** → **Run workflow** → **Run workflow**.
2. It takes 1–3 minutes. A green check means it worked; open your Pages URL to see the result.
3. If it's red, click the run to read the log (common causes: key not added in step 4, or write permission not set in step 5).

You're done. From now on it refreshes on its own, twice a day.

---

## Changing the schedule

You picked **twice daily**. The times live at the top of
`.github/workflows/update.yml`:

```yaml
schedule:
  - cron: "0 22 * * *"   # 22:00 UTC = 06:00 Hong Kong
  - cron: "0 10 * * *"   # 10:00 UTC = 18:00 Hong Kong
```

Cron times are in **UTC**. Convert your local time to UTC, or paste an
expression into **crontab.guru** to check it. A few examples:

| You want (Hong Kong, UTC+8) | Use (UTC) |
|---|---|
| 6:00 am | `0 22 * * *` |
| 6:00 pm | `0 10 * * *` |
| 8:00 am | `0 0 * * *` |
| 9:00 pm | `0 13 * * *` |

- **Once a day instead:** delete one of the two `- cron:` lines.
- **More often:** add lines, e.g. `- cron: "0 */6 * * *"` for every 6 hours.
- **Weekdays only:** change the last field, e.g. `0 22 * * 1-5`.

Edit the file on GitHub (pencil icon), commit, and the new schedule takes effect.

> Note: GitHub's scheduled runs can start a few minutes late when their
> servers are busy — normal, not a fault.

---

## Cost

You pay Anthropic for API usage only (GitHub Pages and Actions are free at
this scale). Each run does four jurisdictions × several web searches plus the
text it writes. As a rough guide that's on the order of **US$0.10–0.40 per
run**, so **twice daily ≈ a few dollars up to ~US$20–25 a month**, depending
on the model and how many searches you allow. To spend less: use a smaller
model (see below), lower `MAX_SEARCHES` in `update_news.py`, or drop to once a
day. Check real numbers under **Usage** in the Anthropic console.

## Tuning (optional)

All the knobs are near the top of `update_news.py`:

- `MODEL` — quality vs. cost. Sonnet is the default sweet spot; an Opus model
  gives richer commentary for more money; a Haiku model is cheapest.
  Confirm current model IDs at docs.claude.com/en/docs/about-claude/models.
- `DISPLAY_TZ` — the timezone shown in the "Auto-updated …" stamp
  (default `Asia/Hong_Kong`).
- `MAX_SEARCHES` — searches allowed per jurisdiction (default 8).
- `JURISDICTIONS` — add, remove, or re-weight countries and their source lists.

---

## Want changes to the design or logic?

Ask me (in Claude / Cowork) — e.g. "add Australia," "make the commentary
sharper and markets-focused," "show a source link on each story," or "switch
to a light theme." I'll hand you an updated `update_news.py` (and/or workflow)
to drop in, replacing the old one. You can also ask me for an on-demand
refresh any time between scheduled runs.

## A caveat worth keeping in mind

The ranking and "public engagement" read are the model's best judgement from
what it can find via web search, not a hard metric — and some major outlets
block automated access, so attributions can occasionally be approximate.
Treat it as a smart daily briefing, and click through to the outlet before
relying on any single item.
