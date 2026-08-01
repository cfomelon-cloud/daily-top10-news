#!/usr/bin/env python3
"""
Render index.html from news_data.json — NO API, no external packages.
Bilingual: every story carries English + Traditional Chinese; the page has a
language toggle (EN / 繁體中文).

news_data.json schema (five keys, each an array of up to 10 items):
{
  "uk": [ {
      "rank":1, "date":"30 Jul 2026", "status":"NEW",     // or "DEVELOPING"
      "outlets":["BBC","Reuters"],
      "headline_en":"...", "headline_zh":"...",
      "summary_en":"...",  "summary_zh":"...",
      "commentary_en":"...","commentary_zh":"..."
  }, ... ],
  "hk":[...], "sg":[...], "us":[...], "cn":[...]
}
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DISPLAY_TZ = "Europe/London"

JURISDICTIONS = [
    {"key": "world", "flag": "\U0001F30D",        "en": "World",            "zh": "國際",     "short_en": "World",     "short_zh": "國際"},
    {"key": "uk", "flag": "\U0001F1EC\U0001F1E7", "en": "United Kingdom",   "zh": "英國",     "short_en": "UK",        "short_zh": "英國"},
    {"key": "hk", "flag": "\U0001F1ED\U0001F1F0", "en": "Hong Kong",        "zh": "香港",     "short_en": "Hong Kong", "short_zh": "香港"},
    {"key": "sg", "flag": "\U0001F1F8\U0001F1EC", "en": "Singapore",        "zh": "新加坡",   "short_en": "Singapore", "short_zh": "新加坡"},
    {"key": "us", "flag": "\U0001F1FA\U0001F1F8", "en": "United States",    "zh": "美國",     "short_en": "US",        "short_zh": "美國"},
    {"key": "cn", "flag": "\U0001F1E8\U0001F1F3", "en": "China (mainland)", "zh": "中國內地", "short_en": "China",     "short_zh": "中國"},
]

CSS = """
  :root{--bg:#0f1115;--panel:#171a21;--panel2:#1d222b;--line:#2a2f3a;--txt:#e8eaed;
    --muted:#9aa2b1;--accent:#4f8cff;--chip:#242a35;--uk:#5b8def;--hk:#e0556b;--sg:#e0a83c;
    --us:#42b98a;--cn:#e23b3b;--world:#8b5cf6;--new:#2ec17c;--dev:#e0a83c;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,
    "Segoe UI",Roboto,Helvetica,Arial,"PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.6;font-size:15px}
  header{padding:24px 20px 14px}
  .hrow{max-width:920px;margin:0 auto;display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
  h1{font-size:22px;margin:0 0 4px;letter-spacing:-.2px}
  .sub{color:var(--muted);font-size:13px;margin:0}
  .langtoggle{display:flex;gap:4px;flex:0 0 auto}
  .langbtn{background:var(--panel);border:1px solid var(--line);color:var(--muted);border-radius:8px;
    padding:6px 11px;font-size:12.5px;font-weight:700;cursor:pointer}
  .langbtn.on{background:var(--accent);border-color:var(--accent);color:#fff}
  .controls{display:flex;flex-direction:column;gap:6px;align-items:flex-end;flex:0 0 auto}
  .voicetoggle{display:flex;gap:4px;align-items:center;font-size:12px;color:var(--muted)}
  .vbtn{background:var(--panel);border:1px solid var(--line);color:var(--muted);border-radius:8px;
    padding:5px 9px;font-size:12px;font-weight:700;cursor:pointer}
  .vbtn.on{background:var(--accent);border-color:var(--accent);color:#fff}
  .speak{background:var(--chip);border:1px solid var(--line);color:var(--muted);border-radius:7px;
    padding:1px 7px;font-size:12px;cursor:pointer;line-height:1.4}
  .speak.playing{background:var(--accent);border-color:var(--accent);color:#fff}
  .playall{background:var(--accent);border:1px solid var(--accent);color:#fff;border-radius:8px;
    padding:6px 12px;font-size:12.5px;font-weight:700;cursor:pointer;white-space:nowrap}
  .playall.on{background:var(--dev);border-color:var(--dev);color:#1a1400}
  .card.reading{outline:2px solid var(--accent);outline-offset:2px}
  .legend{max-width:920px;margin:12px auto 0;padding:0 20px;display:flex;gap:14px;font-size:12px;
    color:var(--muted);align-items:center;flex-wrap:wrap}
  .badge{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;font-weight:700;padding:2px 8px;
    border-radius:20px;letter-spacing:.4px;white-space:nowrap}
  .badge.new{background:rgba(46,193,124,.16);color:var(--new);border:1px solid rgba(46,193,124,.4)}
  .badge.dev{background:rgba(224,168,60,.14);color:var(--dev);border:1px solid rgba(224,168,60,.4)}
  .dot{width:6px;height:6px;border-radius:50%;background:currentColor}
  .tabs{position:sticky;top:0;z-index:5;background:var(--bg);max-width:920px;margin:14px auto 0;
    padding:8px 14px;display:flex;gap:8px;border-bottom:1px solid var(--line);flex-wrap:wrap}
  .tab{flex:1;min-width:88px;text-align:center;padding:9px 6px;border-radius:9px;background:var(--panel);
    border:1px solid var(--line);color:var(--muted);cursor:pointer;font-weight:600;font-size:14px;transition:.15s}
  .tab .flag{font-size:16px;margin-right:5px}
  .tab.active{color:#fff}
  .tab[data-j="uk"].active{background:var(--uk);border-color:var(--uk)}
  .tab[data-j="hk"].active{background:var(--hk);border-color:var(--hk)}
  .tab[data-j="sg"].active{background:var(--sg);border-color:var(--sg);color:#1a1400}
  .tab[data-j="us"].active{background:var(--us);border-color:var(--us);color:#04231a}
  .tab[data-j="cn"].active{background:var(--cn);border-color:var(--cn)}
  .tab[data-j="world"].active{background:var(--world);border-color:var(--world)}
  main{max-width:920px;margin:0 auto;padding:18px 16px 60px}
  .panel{display:none} .panel.active{display:block}
  .panel h2{font-size:16px;margin:6px 4px 14px;color:var(--muted);font-weight:600}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:15px 16px 16px;
    margin-bottom:13px;position:relative;overflow:hidden}
  .card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px}
  .uk .card:before{background:var(--uk)} .hk .card:before{background:var(--hk)}
  .sg .card:before{background:var(--sg)} .us .card:before{background:var(--us)}
  .cn .card:before{background:var(--cn)}
  .world .card:before{background:var(--world)}
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
  body.lang-en .zh{display:none} body.lang-zh .en{display:none}
"""

SCRIPT = """
<script>
function setLang(l){
  document.body.className='lang-'+l;
  document.querySelectorAll('.langbtn').forEach(function(b){b.classList.toggle('on', b.dataset.l===l);});
}
var _tabs=document.querySelectorAll('.tab');
var _panels=document.querySelectorAll('.panel');
_tabs.forEach(function(t){t.addEventListener('click',function(){
  if(typeof stopAll==='function')stopAll();
  _tabs.forEach(function(x){x.classList.remove('active');});
  _panels.forEach(function(p){p.classList.remove('active');});
  t.classList.add('active');
  document.getElementById(t.dataset.j).classList.add('active');
  window.scrollTo({top:0,behavior:'smooth'});
});});
var readLang='en';
function setVoice(v){readLang=v;document.querySelectorAll('.vbtn').forEach(function(b){b.classList.toggle('on',b.dataset.v===v);});if(typeof stopAll==='function')stopAll();}
function _pickVoice(lang){var vs=(window.speechSynthesis.getVoices()||[]);
  var pref=lang==='zh'?['zh-hk','yue','zh-hant','zh-tw','zh']:['en-gb','en-us','en'];
  for(var p=0;p<pref.length;p++){for(var i=0;i<vs.length;i++){if((vs[i].lang||'').toLowerCase().indexOf(pref[p])===0)return vs[i];}}
  if(lang==='zh'){for(var j=0;j<vs.length;j++){var n=(vs[j].name||'').toLowerCase();if(n.indexOf('cantonese')>=0||n.indexOf('sinji')>=0)return vs[j];}}
  return null;}
function _cardText(card){var sel=readLang==='zh'?'.zh':'.en';var parts=[];['h3','.summary','.commentary p'].forEach(function(q){var el=card.querySelector(q+' '+sel);if(el&&el.textContent)parts.push(el.textContent);});return parts.join('. ');}
function _mkUtter(text){var u=new SpeechSynthesisUtterance(text);u.lang=readLang==='zh'?'zh-HK':'en-GB';var v=_pickVoice(readLang);if(v)u.voice=v;u.rate=readLang==='zh'?0.95:1.0;return u;}
var _queue=[],_qi=0,_playingAll=false;
function stopAll(){_playingAll=false;_queue=[];_qi=0;if('speechSynthesis' in window)window.speechSynthesis.cancel();
  document.querySelectorAll('.speak.playing').forEach(function(b){b.classList.remove('playing');});
  document.querySelectorAll('.card.reading').forEach(function(c){c.classList.remove('reading');});
  var pb=document.getElementById('playall');if(pb){pb.classList.remove('on');pb.textContent='▶ Play all';}}
function _next(){
  if(!_playingAll||_qi>=_queue.length){stopAll();return;}
  var card=_queue[_qi];
  document.querySelectorAll('.card.reading').forEach(function(c){c.classList.remove('reading');});
  card.classList.add('reading');
  try{card.scrollIntoView({behavior:'smooth',block:'center'});}catch(e){}
  var u=_mkUtter(_cardText(card));
  u.onend=function(){_qi++;_next();};
  u.onerror=function(){_qi++;_next();};
  window.speechSynthesis.speak(u);
}
function playAll(){
  if(!('speechSynthesis' in window)){alert('Read-aloud is not supported in this browser.');return;}
  if(_playingAll){stopAll();return;}
  var panel=document.querySelector('.panel.active');
  if(!panel)return;
  _queue=Array.prototype.slice.call(panel.querySelectorAll('.card'));
  if(!_queue.length)return;
  _qi=0;_playingAll=true;
  var pb=document.getElementById('playall');if(pb){pb.classList.add('on');pb.textContent='⏸ Stop';}
  _next();
}
function speakCard(btn){
  if(!('speechSynthesis' in window)){alert('Read-aloud is not supported in this browser.');return;}
  var wasPlaying=btn.classList.contains('playing');
  stopAll();
  if(wasPlaying)return;
  var card=btn.closest('.card');
  var u=_mkUtter(_cardText(card));
  u.onend=function(){btn.classList.remove('playing');};
  u.onerror=function(){btn.classList.remove('playing');};
  btn.classList.add('playing');
  window.speechSynthesis.speak(u);
}
if('speechSynthesis' in window){window.speechSynthesis.getVoices();window.speechSynthesis.onvoiceschanged=function(){};}
</script>
"""


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bl(en, zh):
    """Bilingual inline span pair."""
    return f'<span class="en">{esc(en)}</span><span class="zh">{esc(zh or en)}</span>'


def render_card(item):
    status = str(item.get("status", "")).strip().upper()
    is_new = status.startswith("NEW")
    badge_cls = "new" if is_new else "dev"
    badge = bl("NEW", "最新") if is_new else bl("DEVELOPING", "發展中")
    outlets = "".join(f'<span class="chip">{esc(o)}</span>' for o in item.get("outlets", []))
    return (
        '\n  <div class="card"><div class="head">'
        f'<span class="rank">{esc(item.get("rank",""))}</span>'
        f'<h3>{bl(item.get("headline_en",""), item.get("headline_zh",""))}</h3></div>\n'
        f'  <div class="meta"><span class="badge {badge_cls}"><span class="dot"></span>{badge}</span>'
        f'<span class="date">{esc(item.get("date",""))}</span>'
        f'<button class="speak" title="Read aloud / 朗讀" onclick="speakCard(this)">\U0001F50A</button></div>\n'
        f'  <div class="outlets">{outlets}</div>\n'
        f'  <span class="lbl">{bl("Summary","摘要")}</span>'
        f'<p class="summary">{bl(item.get("summary_en",""), item.get("summary_zh",""))}</p>\n'
        f'  <div class="commentary"><span class="lbl">{bl("Commentary","評論")}</span>'
        f'<p>{bl(item.get("commentary_en",""), item.get("commentary_zh",""))}</p></div></div>'
    )


def render_html(data, disp):
    tabs, panels = "", ""
    for i, j in enumerate(JURISDICTIONS):
        active = " active" if i == 0 else ""
        tabs += (f'  <div class="tab{active}" data-j="{j["key"]}"><span class="flag">{j["flag"]}</span>'
                 f'{bl(j["short_en"], j["short_zh"])}</div>\n')
        cards = "".join(render_card(it) for it in data.get(j["key"], []))
        h2 = bl(f'{j["en"]} — top 10', f'{j["zh"]} — 十大新聞')
        panels += f'<section class="panel {j["key"]}{active}" id="{j["key"]}">\n  <h2>{h2}</h2>\n{cards}\n</section>\n'

    names_en = " · ".join(j["short_en"] for j in JURISDICTIONS)
    names_zh = " · ".join(j["short_zh"] for j in JURISDICTIONS)
    h1 = bl(f"Daily Top 10 — {names_en}", f"每日十大新聞 — {names_zh}")
    sub = bl(f"Updated {disp} · ranked by prominence + engagement + recency",
             f"更新於 {disp} · 按重要性、關注度及時效排序")
    legend = (
        '<div class="legend">\n'
        f'  <span class="badge new"><span class="dot"></span>{bl("NEW","最新")}</span> '
        f'{bl("broke or updated in the last 24h","24小時內發生或更新")}\n'
        f'  <span class="badge dev"><span class="dot"></span>{bl("DEVELOPING","發展中")}</span> '
        f'{bl("older but still active — shows age &amp; last update","較早但仍在發展 — 顯示時間")}\n'
        '</div>'
    )
    foot = bl(
        "Updated automatically via live web search. Summaries are neutral; commentary is analytical and "
        "non-partisan. Each feed leads with last-24-hour stories; older items are tagged DEVELOPING. "
        "Always check a headline against the linked outlet before relying on it.",
        "由即時網絡搜尋自動更新。摘要力求中立，評論為分析性質且不偏不倚。每個地區以最近24小時的新聞為主，"
        "較早的新聞標示為「發展中」。引用前請以原始新聞機構為準。")

    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>Daily Top 10 · 每日十大新聞</title>\n<style>{CSS}</style>\n</head>\n'
        '<body class="lang-en">\n'
        f'<header><div class="hrow"><div><h1>{h1}</h1><p class="sub">{sub}</p></div>'
        '<div class="controls">'
        '<div class="langtoggle">'
        '<button class="langbtn on" data-l="en" onclick="setLang(\'en\')">EN</button>'
        '<button class="langbtn" data-l="zh" onclick="setLang(\'zh\')">繁體</button>'
        '</div>'
        '<div class="voicetoggle"><span>\U0001F50A</span>'
        '<button class="vbtn on" data-v="en" onclick="setVoice(\'en\')">EN</button>'
        '<button class="vbtn" data-v="zh" onclick="setVoice(\'zh\')">粵</button>'
        '</div>'
        '<button id="playall" class="playall" onclick="playAll()">▶ Play all</button>'
        '</div></div></header>\n'
        f'{legend}\n<nav class="tabs">\n{tabs}</nav>\n<main>\n{panels}</main>\n'
        f'<footer>{foot}</footer>\n{SCRIPT}\n</body>\n</html>\n'
    )


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
