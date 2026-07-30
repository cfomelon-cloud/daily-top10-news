#!/usr/bin/env python3
"""
Render index.html from news_data.json — NO API, no external packages.

The scheduled Cowork job writes the day's research into news_data.json
(see the schema below) and then runs `python3 build_page.py`, which
regenerates index.html with consistent styling.

news_data.json schema:
{
  "uk": [ {"rank":1,"headline":"...","date":"30 Jul 2026","status":"NEW",
           "outlets":["BBC","Reuters"],"summary":"...","commentary":"..."}, ... ],
  "hk": [ ... ], "sg": [ ... ], "us": [ ... ], "cn": [ ... ]
}
status is either "NEW" or "DEVELOPING - <detail>".
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DISPLAY_TZ = "Europe/London"   # timestamp shown on the page

JURISDICTIONS = [
    {"key": "uk", "name": "United Kingdom",   "flag": "\U0001F1EC\U0001F1E7", "short": "UK"},
    {"key": "hk", "name": "Hong Kong",        "flag": "\U0001F1ED\U0001F1F0", "short": "Hong Kong"},
    {"key": "sg", "name": "Singapore",        "flag": "\U0001F1F8\U0001F1EC", "short": "Singapore"},
    {"key": "us", "name": "United States",    "flag": "\U0001F1FA\U0001F1F8", "short": "US"},
    {"key": "cn", "name": "China (mainland)", "flag": "\U0001F1E8\U0001F1F3", "short": "China"},
]

CSS = """
  :root{--bg:#0f1115;--panel:#171a21;--panel2:#1d222b;--line:#2a2f3a;--txt:#e8eaed;
    --muted:#9aa2b1;--accent:#4f8cff;--chip:#242a35;--uk:#5b8def;--hk:#e0556b;--sg:#e0a83c;
    --us:#42b98a;--cn:#e23b3b;--new:#2ec17c;--dev:#e0a83c;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,
    "Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55;font-size:15px}
  header{padding:26px 20px 16px;max-width:920px;margin:0 auto}
  h1{font-size:23px;margin:0 0 4px;letter-spacing:-.2px}
  .sub{color:var(--muted);font-size:13.5px;margin:0}
  .legend{max-width:920px;margin:12px auto 0;padding:0 20px;display:flex;gap:14px;font-size:12px;
    color:var(--muted);align-items:center;flex-wrap:wrap}
  .badge{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;font-weight:700;padding:2px 8px;
    border-radius:20px;letter-spacing:.4px;white-space:nowrap}
  .badge.new{background:rgba(46,193,124,.16);color:var(--new);border:1px solid rgba(46,193,124,.4)}
  .badge.dev{background:rgba(224,168,60,.14);color:var(--dev);border:1px solid rgba(224,168,60,.4)}
  .dot{width:6px;height:6px;border-radius:50%;background:currentColor}
  .tabs{position:sticky;top:0;z-index:5;background:var(--bg);max-width:920px;margin:14px auto 0;
    padding:8px 14px;display:flex;gap:8px;border-bottom:1px solid var(--line);flex-wrap:wrap}
  .tab{flex:1;min-width:90px;text-align:center;padding:9px 6px;border-radius:9px;background:var(--panel);
    border:1px solid var(--line);color:var(--muted);cursor:pointer;font-weight:600;font-size:14px;transition:.15s}
  .tab .flag{font-size:16px;margin-right:5px}
  .tab.active{color:#fff}
  .tab[data-j="uk"].active{background:var(--uk);border-color:var(--uk)}
  .tab[data-j="hk"].active{background:var(--hk);border-color:var(--hk)}
  .tab[data-j="sg"].active{background:var(--sg);border-color:var(--sg);color:#1a1400}
  .tab[data-j="us"].active{background:var(--us);border-color:var(--us);color:#04231a}
  .tab[data-j="cn"].active{background:var(--cn);border-color:var(--cn)}
  main{max-width:920px;margin:0 auto;padding:18px 16px 60px}
  .panel{display:none} .panel.active{display:block}
  .panel h2{font-size:16px;margin:6px 4px 14px;color:var(--muted);font-weight:600}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:15px 16px 16px;
    margin-bottom:13px;position:relative;overflow:hidden}
  .card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px}
  .uk .card:before{background:var(--uk)} .hk .card:before{background:var(--hk)}
  .sg .card:before{background:var(--sg)} .us .card:before{background:var(--us)}
  .cn .card:before{background:var(--cn)}
  .rank{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:7px;
    background:var(--chip);font-weight:700;font-size:14px;margin-right:9px;color:var(--txt);flex:0 0 auto}
  .head{display:flex;align-items:flex-start;margin-bottom:7px}
  .head h3{font-size:15.5px;margin:1px 0 0;font-weight:650;letter-spacing:-.1px}
  .meta{display:flex;align-items:center;gap:8px;margin:0 0 9px 35px;flex-wrap:wrap}
  .date{font-size:11.5px;color:var(--muted)}
  .outlets{margin:0 0 10px 35px;display:flex;flex-wrap:wrap;gap:5px}
  .chip{background:var(--chip);color:var(--muted);font-size:11px;padding:2px 8px;border-radius:20px;white-space:nowrap}
  .lbl{font-size:10.5px;letter-spacing:.7px;text-transform:uppercase;color:var(--muted);font-weight:700;
    display:block;margin:0 0 2px}
  .summary{margin:0 0 11px}
  .commentary{background:var(--panel2);border-radius:9px;padding:10px 12px;border-left:2px solid var(--accent)}
  .commentary p{margin:0;color:#d3d8e2;font-size:14px}
  footer{max-width:920px;margin:0 auto;padding:0 20px 50px;color:var(--muted);font-size:12px}
"""


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_card(item):
    status = str(item.get("status", "")).strip()
    is_new = status.upper().startswith("NEW")
    badge_cls = "new" if is_new else "dev"
    badge_txt = "NEW" if is_new else "DEVELOPING"
    extra = ""
    if not is_new and "-" in status:
        extra = " · " + esc(status.split("-", 1)[1].strip())
    outlets = "".join(f'<span class="chip">{esc(o)}</span>' for o in item.get("outlets", []))
    return (
        f'\n  <div class="card"><div class="head"><span class="rank">{esc(item.get("rank",""))}</span>'
        f'<h3>{esc(item.get("headline",""))}</h3></div>\n'
        f'  <div class="meta"><span class="badge {badge_cls}"><span class="dot"></span>{badge_txt}{extra}</span>'
        f'<span class="date">{esc(item.get("date",""))}</span></div>\n'
        f'  <div class="outlets">{outlets}</div>\n'
        f'  <span class="lbl">Summary</span><p class="summary">{esc(item.get("summary",""))}</p>\n'
        f'  <div class="commentary"><span class="lbl">Commentary</span><p>{esc(item.get("commentary",""))}</p></div></div>'
    )


def render_html(data, generated_display):
    tabs, panels = "", ""
    for i, j in enumerate(JURISDICTIONS):
        active = " active" if i == 0 else ""
        tabs += (f'  <div class="tab{active}" data-j="{j["key"]}">'
                 f'<span class="flag">{j["flag"]}</span>{j["short"]}</div>\n')
        cards = "".join(render_card(it) for it in data.get(j["key"], []))
        panels += (f'<section class="panel {j["key"]}{active}" id="{j["key"]}">\n'
                   f'  <h2>{esc(j["name"])} — top 10</h2>\n{cards}\n</section>\n')
    names = " · ".join(j["short"] for j in JURISDICTIONS)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Top 10 — {esc(names)}</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Daily Top 10 — {esc(names)}</h1>
  <p class="sub">Updated {esc(generated_display)} · ranked by prominence + engagement + recency</p>
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
  Updated automatically via live web search. Summaries are neutral; commentary is analytical and non-partisan.
  Each feed leads with last-24-hour stories; older items are tagged DEVELOPING with their age. Always sanity-check
  a headline against the linked outlet before relying on it.
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


def main():
    with open("news_data.json", encoding="utf-8") as f:
        data = json.load(f)
    disp = datetime.now(timezone.utc).astimezone(ZoneInfo(DISPLAY_TZ)).strftime("%a %d %b %Y, %H:%M %Z")
    html = render_html(data, disp)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    total = sum(len(data.get(j["key"], [])) for j in JURISDICTIONS)
    print(f"Wrote index.html ({len(html)} bytes, {total} stories) at {disp}")


if __name__ == "__main__":
    main()
