#!/usr/bin/env python3
"""
Daily Top 10 news generator.

For each jurisdiction (UK, Hong Kong, Singapore, US) this script asks the
Claude API (with the built-in web_search tool) to compile the day's top 10
stories under a strict-recency rule, then regenerates index.html.

Run locally:   ANTHROPIC_API_KEY=sk-ant-... python update_news.py
In CI:         the GitHub Actions workflow sets ANTHROPIC_API_KEY from a secret.
"""

import os
import re
import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import anthropic

# --------------------------------------------------------------------------
# CONFIG — safe to edit
# --------------------------------------------------------------------------

# Confirm the current model IDs at https://docs.claude.com/en/docs/about-claude/models
# Sonnet is the cost/quality sweet spot for this job. Swap to an Opus model
# for richer commentary (higher cost), or a Haiku model to cut cost.
MODEL = "claude-sonnet-4-5"

# Timezone used for the "last updated" stamp shown on the page.
DISPLAY_TZ = "Asia/Hong_Kong"   # e.g. "Europe/London", "America/New_York"

# How many web searches the model may run per jurisdiction. More = more
# thorough but more expensive. 6–10 is a good range.
MAX_SEARCHES = 8

ITEMS_PER_JURISDICTION = 10

JURISDICTIONS = [
    {"key": "uk", "name": "United Kingdom", "flag": "\U0001F1EC\U0001F1E7", "short": "UK",
     "sources": "reputable UK outlets (BBC, The Guardian, The Times, Financial Times, "
                "The Telegraph, Sky News, The Independent, Reuters UK)"},
    {"key": "hk", "name": "Hong Kong", "flag": "\U0001F1ED\U0001F1F0", "short": "Hong Kong",
     "sources": "reputable Hong Kong outlets in BOTH English (SCMP, The Standard, RTHK, HKFP) "
                "AND Chinese (明報 Ming Pao, 星島 Sing Tao, 東方日報 Oriental Daily, "
                "香港01 HK01, 信報, 文匯報/大公報) — search Chinese-language queries too"},
    {"key": "sg", "name": "Singapore", "flag": "\U0001F1F8\U0001F1EC", "short": "Singapore",
     "sources": "reputable Singapore outlets (The Straits Times, CNA, TODAY, The Business Times, "
                "Mothership, and 联合早报 Lianhe Zaobao where appropriate)"},
    {"key": "us", "name": "United States", "flag": "\U0001F1FA\U0001F1F8", "short": "US",
     "sources": "reputable US outlets (New York Times, Washington Post, Wall Street Journal, AP, "
                "Reuters, CNN, NBC News, Politico, Axios, CNBC)"},
]

# --------------------------------------------------------------------------
# PROMPTING
# --------------------------------------------------------------------------

def build_prompt(j, today_str):
    return f"""Today is {today_str}. Compile the TOP {ITEMS_PER_JURISDICTION} news stories in {j['name']} right now.

Use the web_search tool to find CURRENT stories — do not rely on memory. Draw on {j['sources']}. Prefer stories confirmed by two or more outlets.

RANKING (in order): (1) prominence given by these outlets — lead/front-page/most-covered; (2) how heavily the story is discussed and commented on online; (3) recency as a strong factor.

STRICT RECENCY RULE:
- Strongly prioritise stories that broke or had a material new development in the last ~24 hours.
- Include an older ongoing story ONLY if it is still actively developing and dominating coverage today; mark it as developing.
- Do NOT include a story whose main event is more than ~24h old with no fresh development.
- Aim for at least 7 of the {ITEMS_PER_JURISDICTION} to be genuinely NEW (last 24h).

Return ONLY a JSON object (no prose, no markdown fences) in exactly this shape:
{{
  "items": [
    {{
      "rank": 1,
      "headline": "clear one-line headline (for HK, add the Chinese headline in parentheses if the story is primarily from Chinese sources)",
      "date": "date of the core event or latest development, e.g. '29 Jul 2026'",
      "status": "NEW" or "DEVELOPING - X days old, last update <date>",
      "outlets": ["Outlet A", "Outlet B"],
      "summary": "2-3 neutral, factual sentences",
      "commentary": "2-3 sentences of balanced, non-partisan analytical commentary: why it matters, what to watch"
    }}
    // ... {ITEMS_PER_JURISDICTION} items, ranked 1 (most important) to {ITEMS_PER_JURISDICTION}
  ]
}}"""


def extract_json(text):
    """Pull the outermost JSON object out of the model's final text."""
    text = text.strip()
    # strip code fences if present
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start:end + 1])


def fetch_jurisdiction(client, j, today_str):
    print(f"  -> researching {j['name']} ...", flush=True)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}],
        messages=[{"role": "user", "content": build_prompt(j, today_str)}],
    )
    # Collect all text blocks from the final assistant message.
    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
    data = extract_json(text)
    items = data["items"][:ITEMS_PER_JURISDICTION]
    if not items:
        raise ValueError(f"No items returned for {j['name']}")
    return items

# --------------------------------------------------------------------------
# HTML RENDERING
# --------------------------------------------------------------------------

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_card(item):
    status = str(item.get("status", "")).strip()
    is_new = status.upper().startswith("NEW")
    badge_cls = "new" if is_new else "dev"
    badge_txt = "NEW" if is_new else "DEVELOPING"
    # keep any extra detail after "DEVELOPING -" in the badge subtitle
    extra = ""
    if not is_new and "-" in status:
        extra = " · " + esc(status.split("-", 1)[1].strip())
    outlets = "".join(f'<span class="chip">{esc(o)}</span>' for o in item.get("outlets", []))
    return f"""
  <div class="card"><div class="head"><span class="rank">{esc(item.get('rank',''))}</span><h3>{esc(item.get('headline',''))}</h3></div>
  <div class="meta"><span class="badge {badge_cls}"><span class="dot"></span>{badge_txt}{extra}</span><span class="date">{esc(item.get('date',''))}</span></div>
  <div class="outlets">{outlets}</div>
  <span class="lbl">Summary</span><p class="summary">{esc(item.get('summary',''))}</p>
  <div class="commentary"><span class="lbl">Commentary</span><p>{esc(item.get('commentary',''))}</p></div></div>"""


def render_html(data_by_key, generated_display):
    tabs = ""
    panels = ""
    for i, j in enumerate(JURISDICTIONS):
        active = " active" if i == 0 else ""
        tabs += (f'<div class="tab{active}" data-j="{j["key"]}">'
                 f'<span class="flag">{j["flag"]}</span>{j["short"]}</div>\n')
        cards = "".join(render_card(it) for it in data_by_key.get(j["key"], []))
        panels += (f'<section class="panel {j["key"]}{active}" id="{j["key"]}">\n'
                   f'  <h2>{esc(j["name"])} — top {ITEMS_PER_JURISDICTION}</h2>\n{cards}\n</section>\n')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Top 10 — UK · HK · SG · US</title>
<style>
  :root{{--bg:#0f1115;--panel:#171a21;--panel2:#1d222b;--line:#2a2f3a;--txt:#e8eaed;
    --muted:#9aa2b1;--accent:#4f8cff;--chip:#242a35;--uk:#5b8def;--hk:#e0556b;--sg:#e0a83c;
    --us:#42b98a;--new:#2ec17c;--dev:#e0a83c;}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,
    "Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55;font-size:15px}}
  header{{padding:26px 20px 16px;max-width:920px;margin:0 auto}}
  h1{{font-size:23px;margin:0 0 4px;letter-spacing:-.2px}}
  .sub{{color:var(--muted);font-size:13.5px;margin:0}}
  .legend{{max-width:920px;margin:12px auto 0;padding:0 20px;display:flex;gap:14px;font-size:12px;
    color:var(--muted);align-items:center;flex-wrap:wrap}}
  .badge{{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;font-weight:700;padding:2px 8px;
    border-radius:20px;letter-spacing:.4px;white-space:nowrap}}
  .badge.new{{background:rgba(46,193,124,.16);color:var(--new);border:1px solid rgba(46,193,124,.4)}}
  .badge.dev{{background:rgba(224,168,60,.14);color:var(--dev);border:1px solid rgba(224,168,60,.4)}}
  .dot{{width:6px;height:6px;border-radius:50%;background:currentColor}}
  .tabs{{position:sticky;top:0;z-index:5;background:var(--bg);max-width:920px;margin:14px auto 0;
    padding:8px 14px;display:flex;gap:8px;border-bottom:1px solid var(--line);flex-wrap:wrap}}
  .tab{{flex:1;min-width:90px;text-align:center;padding:9px 6px;border-radius:9px;background:var(--panel);
    border:1px solid var(--line);color:var(--muted);cursor:pointer;font-weight:600;font-size:14px;transition:.15s}}
  .tab .flag{{font-size:16px;margin-right:5px}}
  .tab.active{{color:#fff}}
  .tab[data-j="uk"].active{{background:var(--uk);border-color:var(--uk)}}
  .tab[data-j="hk"].active{{background:var(--hk);border-color:var(--hk)}}
  .tab[data-j="sg"].active{{background:var(--sg);border-color:var(--sg);color:#1a1400}}
  .tab[data-j="us"].active{{background:var(--us);border-color:var(--us);color:#04231a}}
  main{{max-width:920px;margin:0 auto;padding:18px 16px 60px}}
  .panel{{display:none}} .panel.active{{display:block}}
  .panel h2{{font-size:16px;margin:6px 4px 14px;color:var(--muted);font-weight:600}}
  .card{{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:15px 16px 16px;
    margin-bottom:13px;position:relative;overflow:hidden}}
  .card:before{{content:"";position:absolute;left:0;top:0;bottom:0;width:4px}}
  .uk .card:before{{background:var(--uk)}} .hk .card:before{{background:var(--hk)}}
  .sg .card:before{{background:var(--sg)}} .us .card:before{{background:var(--us)}}
  .rank{{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:7px;
    background:var(--chip);font-weight:700;font-size:14px;margin-right:9px;color:var(--txt);flex:0 0 auto}}
  .head{{display:flex;align-items:flex-start;margin-bottom:7px}}
  .head h3{{font-size:15.5px;margin:1px 0 0;font-weight:650;letter-spacing:-.1px}}
  .meta{{display:flex;align-items:center;gap:8px;margin:0 0 9px 35px;flex-wrap:wrap}}
  .date{{font-size:11.5px;color:var(--muted)}}
  .outlets{{margin:0 0 10px 35px;display:flex;flex-wrap:wrap;gap:5px}}
  .chip{{background:var(--chip);color:var(--muted);font-size:11px;padding:2px 8px;border-radius:20px;white-space:nowrap}}
  .lbl{{font-size:10.5px;letter-spacing:.7px;text-transform:uppercase;color:var(--muted);font-weight:700;
    display:block;margin:0 0 2px}}
  .summary{{margin:0 0 11px}}
  .commentary{{background:var(--panel2);border-radius:9px;padding:10px 12px;border-left:2px solid var(--accent)}}
  .commentary p{{margin:0;color:#d3d8e2;font-size:14px}}
  footer{{max-width:920px;margin:0 auto;padding:0 20px 50px;color:var(--muted);font-size:12px}}
</style>
</head>
<body>
<header>
  <h1>Daily Top 10 — UK · Hong Kong · Singapore · US</h1>
  <p class="sub">Auto-updated {esc(generated_display)} · ranked by prominence + engagement + recency</p>
</header>
<div class="legend">
  <span class="badge new"><span class="dot"></span>NEW</span> broke or updated in the last 24h
  <span class="badge dev"><span class="dot"></span>DEVELOPING</span> older but still active — shows age &amp; last update
</div>
<nav class="tabs">
{tabs}</nav>
<main>
{panels}</main>
<footer>
  Generated automatically by the Claude API with live web search. Summaries are neutral; commentary is
  analytical and non-partisan. Each feed leads with last-24-hour stories; older items are tagged DEVELOPING
  with their age. Always sanity-check a headline against the linked outlet before relying on it.
</footer>
<script>
  const tabs=document.querySelectorAll('.tab');
  const panels=document.querySelectorAll('.panel');
  tabs.forEach(t=>t.addEventListener('click',()=>{{
    tabs.forEach(x=>x.classList.remove('active'));
    panels.forEach(p=>p.classList.remove('active'));
    t.classList.add('active');
    document.getElementById(t.dataset.j).classList.add('active');
    window.scrollTo({{top:0,behavior:'smooth'}});
  }}));
</script>
</body>
</html>
"""

# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ERROR: ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic()

    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.astimezone(ZoneInfo(DISPLAY_TZ)).strftime("%A, %d %B %Y")
    generated_display = now_utc.astimezone(ZoneInfo(DISPLAY_TZ)).strftime("%a %d %b %Y, %H:%M %Z")

    data_by_key = {}
    for j in JURISDICTIONS:
        try:
            data_by_key[j["key"]] = fetch_jurisdiction(client, j, today_str)
        except Exception as e:
            print(f"  !! {j['name']} failed: {e}", flush=True)
            data_by_key[j["key"]] = [{
                "rank": 1, "headline": f"Update failed for {j['name']} — will retry next run",
                "date": generated_display, "status": "DEVELOPING", "outlets": [],
                "summary": "The automated fetch did not return valid results this cycle.",
                "commentary": f"Error: {e}",
            }]

    html = render_html(data_by_key, generated_display)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote index.html ({len(html)} bytes) at {generated_display}", flush=True)


if __name__ == "__main__":
    main()
