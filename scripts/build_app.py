#!/usr/bin/env python3
"""Build a self-contained HTML app from all weekly reports."""

import sys, re, json
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent / "weekly-reports"


def parse_report(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    body = raw
    fm = {}
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        for line in parts[1].strip().split("\n"):
            m = re.match(r'(\w+):\s*"(.+)"', line)
            if m:
                fm[m.group(1)] = m.group(2)
        body = parts[2] if len(parts) > 2 else raw

    # Extract summary from trends section
    trends_match = re.search(r"## .*趋势.*\n\n(.+?)(?=\n## )", body, re.DOTALL)
    summary = ""
    if trends_match:
        paras = [p.strip() for p in trends_match.group(1).split("\n\n") if p.strip()]
        summary = " ".join(p.replace("**", "")[:200] for p in paras[:2])

    # Extract keywords
    kw_match = re.search(r"本周关键词\s*\|\s*(.+?)\s*\|", body)
    keywords = kw_match.group(1).strip() if kw_match else ""

    # Extract knowledge items
    knowledge = []
    lines = body.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        # Match ### or #### heading as item title
        m = re.match(r"^(###|####) (.+)", line)
        if m:
            title = m.group(2).strip()
            depth = len(m.group(1))  # 3 or 4

            # Find section (##) by backtracking
            section = ""
            for j in range(i - 1, -1, -1):
                prev = lines[j].strip()
                sm = re.match(r"^## [🔬🏢🌏]\s*(.+)", prev)
                if sm:
                    section = sm.group(1).strip()
                    break

            # Find sub-category: only for #### items, backtrack to nearest ###
            sub = ""
            if depth == 4:
                for j in range(i - 1, -1, -1):
                    prev = lines[j].strip()
                    if re.match(r"^## ", prev):
                        break
                    if re.match(r"^### (.+)", prev):
                        sub = re.match(r"^### (.+)", prev).group(1).strip()
                        break

            what, why, source, link = "", "", "", ""
            # Look ahead for metadata
            for k in range(i + 1, min(i + 12, len(lines))):
                nl = lines[k].strip()
                if not nl:
                    continue
                if re.match(r"^- \*\*(摘要|发生了什么)\*\*[：:]", nl):
                    what = re.sub(r"^- \*\*(摘要|发生了什么)\*\*[：:]\s*", "", nl)
                elif re.match(r"^- \*\*为什么重要\*\*[：:]", nl):
                    why = re.sub(r"^- \*\*为什么重要\*\*[：:]\s*", "", nl)
                elif re.match(r"^- \*\*来源\*\*[：:]", nl):
                    source = re.sub(r"^- \*\*来源\*\*[：:]\s*", "", nl)
                elif re.match(r"^- \*\*链接\*\*[：:]", nl):
                    link = re.sub(r"^- \*\*链接\*\*[：:]\s*", "", nl)
                elif re.match(r"^(###|####|##) ", nl) or nl == "---":
                    break

            if what or why:
                knowledge.append({
                    "section": section,
                    "sub": sub,
                    "title": title,
                    "what": what,
                    "why": why,
                    "source": source,
                    "link": link,
                })
        i += 1

    return {
        "id": path.stem,
        "title": fm.get("title", path.stem),
        "date": fm.get("date", ""),
        "period": fm.get("period", ""),
        "summary": summary[:300],
        "keywords": keywords,
        "body": md_to_html_body(body),
        "knowledge": knowledge,
    }


def md_to_html_body(body):
    """Convert markdown body to HTML for in-app display."""
    lines = body.split("\n")
    out = []
    in_code, in_list, in_table = False, False, False

    for line in lines:
        s = line.strip()
        if s.startswith("```"):
            out.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            out.append(esc(line))
            continue
        if s == "---":
            out.append("<hr>")
            continue
        if "|" in s and s.startswith("|"):
            if not in_table:
                in_table = True
                out.append("<table>")
            cells = [c.strip() for c in s.split("|")[1:-1]]
            if all(re.match(r"^[-:]+$", c) for c in cells):
                continue
            tag = "th" if in_table and out[-1] == "<table>" else "td"
            out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        elif in_table:
            out.append("</table>")
            in_table = False
            in_list = False

        if s.startswith("# "): out.append(f"<h1>{inline(s[2:])}</h1>"); in_list = False; continue
        if s.startswith("## "): out.append(f"<h2>{inline(s[3:])}</h2>"); in_list = False; continue
        if s.startswith("### "): out.append(f"<h3>{inline(s[4:])}</h3>"); in_list = False; continue
        if s.startswith("#### "): out.append(f"<h4>{inline(s[5:])}</h4>"); in_list = False; continue

        if re.match(r"^\s*[-*]\s+", s):
            if not in_list: out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(re.sub(r'^\s*[-*]\s+', '', s))}</li>")
            continue
        elif in_list:
            out.append("</ul>"); in_list = False

        if s.startswith("> "):
            out.append(f"<blockquote><p>{inline(s[2:])}</p></blockquote>")
            continue
        if s:
            out.append(f"<p>{inline(s)}</p>")
    return "\n".join(out)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(t):
    t = esc(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', t)
    t = re.sub(r'(?<!["=])(https?://[^\s)\]<>\"\u201c\u201d，。]+)', r'<a href="\1" target="_blank">\1</a>', t)
    return t


# ── HTML Template (single-file app) ──

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>AI Weekly</title>
<style>
:root{
  --bg:#f5f5f5;--card-bg:#fff;--text:#1a1a1a;--text2:#6b7280;--text3:#9ca3af;
  --header:#2563eb;--header-text:#fff;--tab-bg:#fff;--tab-border:#e5e7eb;
  --accent:#2563eb;--tag-bg:#dbeafe;--tag-text:#1e40af;--border:#e5e7eb;
  --hover:#f3f4f6;--code-bg:#f1f5f9;--quote-bg:#f8fafc;--font:14px;
}
.dark{
  --bg:#0f172a;--card-bg:#1e293b;--text:#e2e8f0;--text2:#94a3b8;--text3:#64748b;
  --header:#1e3a5f;--header-text:#e2e8f0;--tab-bg:#1e293b;--tab-border:#334155;
  --accent:#60a5fa;--tag-bg:#1e3a5f;--tag-text:#93c5fd;--border:#334155;
  --hover:#1e293b;--code-bg:#1e293b;--quote-bg:#1e293b;
}
.font-sm{--font:12px}.font-md{--font:14px}.font-lg{--font:16px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);font-size:var(--font);max-width:100vw;overflow-x:hidden;padding-bottom:70px;transition:background .3s,color .3s}
.header{background:var(--header);color:var(--header-text);padding:16px 20px;position:sticky;top:0;z-index:10}
.header h1{font-size:calc(var(--font) + 4px);font-weight:700}
.tab-bar{display:flex;position:fixed;bottom:0;left:0;right:0;background:var(--tab-bg);border-top:1px solid var(--tab-border);z-index:10;height:60px}
.tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:calc(var(--font) - 3px);color:var(--text3);cursor:pointer;border:none;background:none}
.tab.active{color:var(--accent)}.tab svg{width:22px;height:22px;margin-bottom:2px}
.page{display:none;padding:12px 16px}
.page.active{display:block}
.card{background:var(--card-bg);border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.card h3{font-size:calc(var(--font) + 1px);margin-bottom:6px}
.card .date{font-size:calc(var(--font) - 2px);color:var(--text2);margin-bottom:8px}
.card .summary{font-size:calc(var(--font) - 1px);color:var(--text);line-height:1.6}
.card .tags{margin-top:8px;display:flex;flex-wrap:wrap;gap:4px}
.card .tag{background:var(--tag-bg);color:var(--tag-text);font-size:calc(var(--font) - 4px);padding:2px 8px;border-radius:10px}
.card .actions{margin-top:10px;display:flex;gap:8px}
.card .actions button{font-size:calc(var(--font) - 2px);padding:6px 12px;border-radius:8px;border:none;cursor:pointer;background:var(--hover);color:var(--text)}
.card .actions button.fav{background:#fef3c7;color:#92400e}
.knowledge-section{margin-bottom:16px}
.knowledge-section h3{font-size:calc(var(--font) + 1px);color:var(--accent);margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid var(--border)}
.knowledge-item{background:var(--card-bg);border-radius:10px;padding:12px;margin-bottom:8px;box-shadow:0 1px 2px rgba(0,0,0,.06);cursor:pointer}
.knowledge-item:active{opacity:.7}
.knowledge-item .ki-title{font-size:calc(var(--font) - 1px);font-weight:600;margin-bottom:4px}
.knowledge-item .ki-what{font-size:calc(var(--font) - 2px);color:var(--text2);margin-bottom:2px}
.knowledge-item .ki-meta{font-size:calc(var(--font) - 4px);color:var(--text3)}
.detail{background:var(--card-bg);border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:var(--font);line-height:1.8}
.detail h1{font-size:calc(var(--font) + 6px);margin-bottom:16px}
.detail h2{font-size:calc(var(--font) + 2px);color:var(--accent);margin:24px 0 10px;border-bottom:1px solid var(--border);padding-bottom:4px}
.detail h3{font-size:var(--font);margin:16px 0 8px}
.detail h4{font-size:calc(var(--font) - 1px);margin:12px 0 6px}
.detail p{margin:6px 0;font-size:var(--font)}
.detail ul{margin:6px 0 6px 20px}
.detail li{margin:2px 0;font-size:var(--font)}
.detail a{color:var(--accent)}
.detail hr{border:0;border-top:1px solid var(--border);margin:16px 0}
.detail table{border-collapse:collapse;width:100%;margin:10px 0;font-size:calc(var(--font) - 2px)}
.detail th,.detail td{border:1px solid var(--border);padding:6px 10px;text-align:left}
.detail th{background:var(--hover)}
.detail blockquote{border-left:3px solid var(--accent);padding:4px 12px;margin:8px 0;background:var(--quote-bg);color:var(--text2)}
.detail pre{background:var(--code-bg);padding:10px 14px;border-radius:6px;overflow-x:auto}
.detail code{background:var(--code-bg);padding:1px 4px;border-radius:3px}
.detail pre code{background:none;padding:0}
.back-btn{display:inline-flex;align-items:center;gap:4px;font-size:calc(var(--font) - 1px);color:var(--accent);cursor:pointer;border:none;background:none;margin-bottom:12px}
.search-bar{display:flex;gap:8px;margin-bottom:12px}
.search-bar input{flex:1;padding:10px 14px;border-radius:10px;border:1px solid var(--border);font-size:var(--font);outline:none;background:var(--card-bg);color:var(--text)}
.search-bar input:focus{border-color:var(--accent)}
.kb-filter{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px}
.kb-filter button{font-size:calc(var(--font) - 3px);padding:4px 10px;border-radius:12px;border:1px solid #d1d5db;background:#fff;color:#374151;cursor:pointer}.dark .kb-filter button{background:#1e293b;color:#e2e8f0;border-color:#334155}
.kb-filter button.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.settings-group{margin-bottom:20px}
.settings-group h3{font-size:var(--font);color:var(--accent);margin-bottom:10px}
.setting-row{display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border)}
.setting-row .label{font-size:calc(var(--font) - 1px)}
.setting-row .value{font-size:calc(var(--font) - 1px);color:var(--text2)}
.toggle{width:50px;height:28px;background:#d1d5db;border-radius:14px;position:relative;cursor:pointer;transition:background .3s}
.toggle.on{background:var(--accent)}
.toggle::after{content:'';width:24px;height:24px;background:#fff;border-radius:50%;position:absolute;top:2px;left:2px;transition:left .3s}
.toggle.on::after{left:24px}
.font-btns{display:flex;gap:6px}
.font-btns button{width:36px;height:36px;border-radius:50%;border:1px solid var(--border);background:var(--card-bg);color:var(--text);cursor:pointer;font-size:calc(var(--font) - 1px)}
.font-btns button.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.lang-select{padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:var(--card-bg);color:var(--text);font-size:calc(var(--font) - 1px)}
.author-info{text-align:center;padding:20px}
.author-info .name{font-size:calc(var(--font) + 2px);font-weight:600}
.author-info .ver{font-size:calc(var(--font) - 2px);color:var(--text3);margin-top:4px}
</style>
</head>
<body class="">

<div class="header"><h1 data-lang="title">🤖 AI Weekly</h1></div>

<div class="page active" id="page-list">
<div class="search-bar"><input type="text" id="search" data-lang-placeholder="search" oninput="renderList()"></div>
<div id="report-list"></div>
</div>

<div class="page" id="page-detail">
<button class="back-btn" onclick="showPage('list')" data-lang="back">← Back</button>
<div class="detail" id="detail-content"></div>
</div>

<div class="page" id="page-kb">
<div class="kb-filter" id="kb-filter"></div>
<div id="kb-content"></div>
</div>

<div class="page" id="page-kb-detail">
<button class="back-btn" onclick="showPage('kb')" data-lang="back">← Back</button>
<div class="detail" id="kb-detail-content"></div>
</div>

<div class="page" id="page-settings">
<div class="settings-group"><h3 data-lang="appearance">Appearance</h3>
<div class="setting-row"><span class="label" data-lang="dark_mode">Dark Mode</span><div class="toggle" id="dark-toggle" onclick="toggleDark()"></div></div>
<div class="setting-row"><span class="label" data-lang="font_size">Font Size</span>
<div class="font-btns">
<button onclick="setFont('sm')" id="font-sm" data-lang="font_sm">A</button>
<button onclick="setFont('md')" id="font-md" class="active" data-lang="font_md">A</button>
<button onclick="setFont('lg')" id="font-lg" data-lang="font_lg">A</button>
</div></div>
</div>
<div class="settings-group"><h3 data-lang="language">Language</h3>
<div class="setting-row"><span class="label" data-lang="ui_lang">UI Language</span>
<select class="lang-select" id="lang-select" onchange="setLang(this.value)">
<option value="zh-CN" data-lang="zh_cn">简体中文</option>
<option value="zh-TW" data-lang="zh_tw">繁體中文</option>
<option value="en" data-lang="en">English</option>
</select></div></div>
<div class="settings-group"><h3 data-lang="about">About</h3>
<div class="author-info"><div class="name">AI Weekly</div><div class="ver">v2.0 · Auto-generated from 8 sources</div></div></div>
</div>

<div class="tab-bar">
<button class="tab active" data-page="list" onclick="showPage('list')">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
<span data-lang="tab_reports">Reports</span>
</button>
<button class="tab" data-page="kb" onclick="showPage('kb')">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
<span data-lang="tab_kb">Knowledge</span>
</button>
<button class="tab" data-page="settings" onclick="showPage('settings')">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.49.49 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41L9.25 5.35c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 00-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
<span data-lang="tab_settings">Settings</span>
</button>
</div>

<script>
var REPORTS = __REPORTS__;
var KB = __KNOWLEDGE__;
var favs=JSON.parse(localStorage.getItem('aiweekly_favs')||'{}');
var LANG=localStorage.getItem('aiweekly_lang')||'zh-CN';
var DARK=localStorage.getItem('aiweekly_dark')==='true';
var FONT=localStorage.getItem('aiweekly_font')||'md';

var I18N={
  title:{'zh-CN':'🤖 AI Weekly','zh-TW':'🤖 AI Weekly','en':'🤖 AI Weekly'},
  search:{'zh-CN':'搜索周报...','zh-TW':'搜尋週報...','en':'Search reports...'},
  back:{'zh-CN':'← 返回','zh-TW':'← 返回','en':'← Back'},
  tab_reports:{'zh-CN':'周报','zh-TW':'週報','en':'Reports'},
  tab_kb:{'zh-CN':'知识库','zh-TW':'知識庫','en':'Knowledge'},
  tab_settings:{'zh-CN':'设置','zh-TW':'設定','en':'Settings'},
  appearance:{'zh-CN':'外观','zh-TW':'外觀','en':'Appearance'},
  dark_mode:{'zh-CN':'黑夜模式','zh-TW':'黑夜模式','en':'Dark Mode'},
  font_size:{'zh-CN':'字体大小','zh-TW':'字體大小','en':'Font Size'},
  font_sm:{'zh-CN':'小','zh-TW':'小','en':'S'},
  font_md:{'zh-CN':'中','zh-TW':'中','en':'M'},
  font_lg:{'zh-CN':'大','zh-TW':'大','en':'L'},
  language:{'zh-CN':'语言','zh-TW':'語言','en':'Language'},
  ui_lang:{'zh-CN':'界面语言','zh-TW':'界面語言','en':'UI Language'},
  zh_cn:{'zh-CN':'简体中文','zh-TW':'簡體中文','en':'Simplified Chinese'},
  zh_tw:{'zh-CN':'繁體中文','zh-TW':'繁體中文','en':'Traditional Chinese'},
  en:{'zh-CN':'English','zh-TW':'English','en':'English'},
  about:{'zh-CN':'关于','zh-TW':'關於','en':'About'},
  read:{'zh-CN':'阅读','zh-TW':'閱讀','en':'Read'},
  save:{'zh-CN':'☆ 收藏','zh-TW':'☆ 收藏','en':'☆ Save'},
  saved:{'zh-CN':'★ 已收藏','zh-TW':'★ 已收藏','en':'★ Saved'},
  no_reports:{'zh-CN':'没有找到周报','zh-TW':'沒有找到週報','en':'No reports yet'},
  no_kb:{'zh-CN':'暂无知识条目','zh-TW':'暫無知識條目','en':'No knowledge entries'},
  source:{'zh-CN':'来源','zh-TW':'來源','en':'Source'},
};

function t(key){var m=I18N[key];return m?(m[LANG]||m['zh-CN']||key):key;}
function applyLang(){
  document.querySelectorAll('[data-lang]').forEach(function(el){
    if(el.tagName==='OPTION')return;
    var k=el.getAttribute('data-lang');if(k&&I18N[k])el.textContent=t(k);
  });
  document.querySelectorAll('[data-lang-placeholder]').forEach(function(el){
    var k=el.getAttribute('data-lang-placeholder');if(k&&I18N[k])el.placeholder=t(k);
  });
  document.getElementById('lang-select').value=LANG;
  renderList();
  if(document.getElementById('page-kb').classList.contains('active'))renderKB('all');
}
function setLang(l){LANG=l;localStorage.setItem('aiweekly_lang',l);applyLang();}
function toggleDark(){DARK=!DARK;localStorage.setItem('aiweekly_dark',DARK);document.body.classList.toggle('dark',DARK);document.getElementById('dark-toggle').classList.toggle('on',DARK);}
function setFont(s){FONT=s;localStorage.setItem('aiweekly_font',s);document.body.classList.remove('font-sm','font-md','font-lg');document.body.classList.add('font-'+s);document.querySelectorAll('.font-btns button').forEach(function(b){b.classList.toggle('active',b.id==='font-'+s);});}
if(DARK){document.body.classList.add('dark');document.getElementById('dark-toggle').classList.add('on');}
document.body.classList.add('font-'+FONT);
applyLang();

function showPage(name){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  var page=document.getElementById('page-'+name);if(page)page.classList.add('active');
  var tab=document.querySelector('[data-page="'+name+'"]');if(tab)tab.classList.add('active');
  if(name==='kb')renderKB('all');
  if(name==='list')renderList();
}

function renderList(){
  var q=(document.getElementById('search').value||'').toLowerCase();
  var html='';
  REPORTS.filter(function(r){return !q||(r.title+r.summary+r.keywords).toLowerCase().indexOf(q)>=0;}).forEach(function(r){
    var isFav=favs[r.id];
    var tags=(r.keywords||'').split(/[#\s]+/).filter(Boolean).slice(0,6);
    html+='<div class="card"><h3>'+r.title+'</h3><div class="date">'+r.period+'</div><div class="summary">'+r.summary+'</div>';
    if(tags.length)html+='<div class="tags">'+tags.map(function(t){return'<span class="tag">#'+t+'</span>';}).join('')+'</div>';
    html+='<div class="actions"><button data-action="detail" data-id="'+r.id+'">'+t('read')+'</button>';
    html+='<button class="'+(isFav?'fav':'')+'" data-action="fav" data-id="'+r.id+'">'+(isFav?t('saved'):t('save'))+'</button></div></div>';
  });
  if(!REPORTS.filter(function(r){return !q||(r.title+r.summary+r.keywords).toLowerCase().indexOf(q)>=0;}).length)
    html='<div class="card" style="text-align:center;color:var(--text3);padding:40px">'+t('no_reports')+'</div>';
  document.getElementById('report-list').innerHTML=html;
}

function openDetail(id){
  var r=REPORTS.find(function(x){return x.id===id;});
  if(!r)return;
  document.getElementById('detail-content').innerHTML='<h1>'+r.title+'</h1><div class="date">'+r.period+'</div>'+r.body;
  showPage('detail');window.scrollTo(0,0);
}

function toggleFav(id){favs[id]=!favs[id];localStorage.setItem('aiweekly_favs',JSON.stringify(favs));renderList();}

function renderKB(filter){
  var subs={},allSubs=[];
  KB.forEach(function(item){
    var key=item.section+' › '+item.sub;
    if(!subs[key]){subs[key]=[];allSubs.push(key);}
    subs[key].push(item);
  });
  var fhtml='<button class="'+(filter==='all'?'active':'')+'" onclick="renderKB(\\'all\\')">All</button>';
  allSubs.forEach(function(s){fhtml+='<button class="'+(filter===s?'active':'')+'" onclick="renderKB(\\''+s.replace(/'/g,\"\\\\'\")+'\\')">'+s.split(' › ').pop()+'</button>';});
  document.getElementById('kb-filter').innerHTML=fhtml;
  var html='';
  allSubs.forEach(function(key){
    if(filter!=='all'&&filter!==key)return;
    html+='<div class="knowledge-section"><h3>'+key+' ('+subs[key].length+')</h3>';
    subs[key].forEach(function(item){
      html+='<div class="knowledge-item" data-title="'+item.title.replace(/"/g,'&quot;')+'"><div class="ki-title">'+item.title+'</div><div class="ki-what">'+(item.what||item.why||'').substring(0,150)+'</div><div class="ki-meta">'+item.source+'</div></div>';
    });
    html+='</div>';
  });
  document.getElementById('kb-content').innerHTML=html||'<div class="card" style="text-align:center;color:var(--text3);padding:40px">'+t('no_kb')+'</div>';
}

function openKbDetail(title){
  var item=KB.find(function(k){return k.title===title;});
  if(!item)return;
  var html='<h4>'+item.title+'</h4>';
  html+='<p style="color:var(--text3);font-size:calc(var(--font) - 2px)">'+item.section+(item.sub?' › '+item.sub:'')+' · '+t('source')+': '+item.source+'</p><hr>';
  if(item.what){html+='<p><strong>'+item.what+'</strong></p>';}
  if(item.why){html+='<p style="color:var(--text2)">'+item.why+'</p>';}
  if(item.link)html+='<hr><p style="font-size:12px">'+t('source')+': <a href="'+item.link+'" target="_blank">'+(item.link||'').substring(0,80)+'</a></p>';
  document.getElementById('kb-detail-content').innerHTML=html;
  showPage('kb-detail');window.scrollTo(0,0);
}

document.addEventListener('click',function(e){
  var el=e.target.closest('[data-action]');
  if(el){
    var action=el.getAttribute('data-action');
    var id=el.getAttribute('data-id');
    if(action==='detail')openDetail(id);
    if(action==='fav')toggleFav(id);
    if(action==='kb-filter')renderKB(el.getAttribute('data-filter'));
    return;
  }
  el=e.target.closest('.knowledge-item');
  if(el){var title=el.getAttribute('data-title');if(title)openKbDetail(title);}
});

renderList();
</script>
</body>
</html>"""

def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else str(REPORTS_DIR / "app.html")

    reports = []
    all_knowledge = []

    md_files = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    for f in md_files:
        try:
            r = parse_report(f)
            reports.append({
                "id": r["id"], "title": r["title"], "date": r["date"],
                "period": r["period"], "summary": r["summary"],
                "keywords": r["keywords"], "body": r["body"],
            })
            for k in r["knowledge"]:
                k["report_id"] = r["id"]
                k["report_title"] = r["title"]
                all_knowledge.append(k)
        except Exception as e:
            print(f"  skip {f.name}: {e}")

    html = HTML_TPL.replace("__REPORTS__", json.dumps(reports, ensure_ascii=False))
    html = html.replace("__KNOWLEDGE__", json.dumps(all_knowledge, ensure_ascii=False))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"App built: {out_path}  ({len(reports)} reports, {len(all_knowledge)} knowledge items)")


if __name__ == "__main__":
    main()
