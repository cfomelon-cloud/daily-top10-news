# Daily Top 10 — UK · Hong Kong · Singapore · US · China

A self-updating news site. Twice a day (05:00 and 15:00 UK time) a scheduled
Claude (Cowork) task researches the day's top 10 stories in each of five
jurisdictions using live web search, writes the results to `news_data.json`,
runs `build_page.py` to regenerate `index.html`, and pushes it here. GitHub
Pages serves it. No paid API and no server of your own.

- `index.html` — the web page (regenerated on every run).
- `build_page.py` — renders `index.html` from `news_data.json` (stdlib only, no API).

Live site: https://cfomelon-cloud.github.io/daily-top10-news/

To change the schedule, countries, or styling, just ask Claude in the Cowork thread.
