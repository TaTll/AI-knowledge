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

HTML_TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>AI Weekly</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#1a1a1a;max-width:100vw;overflow-x:hidden;padding-bottom:70px}
.header{background:#2563eb;color:#fff;padding:16px 20px;position:sticky;top:0;z-index:10}
.header h1{font-size:18px;font-weight:700}
.tab-bar{display:flex;position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #e5e7eb;z-index:10;height:60px}
.tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:11px;color:#9ca3af;cursor:pointer;border:none;background:none}
.tab.active{color:#2563eb}.tab svg{width:22px;height:22px;margin-bottom:2px}
.page{display:none;padding:12px 16px}
.page.active{display:block}
.card{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.card h3{font-size:15px;margin-bottom:6px}
.card .date{font-size:12px;color:#6b7280;margin-bottom:8px}
.card .summary{font-size:13px;color:#374151;line-height:1.6}
.card .tags{margin-top:8px;display:flex;flex-wrap:wrap;gap:4px}
.card .tag{background:#dbeafe;color:#1e40af;font-size:10px;padding:2px 8px;border-radius:10px}
.card .actions{margin-top:10px;display:flex;gap:8px}
.card .actions button{font-size:12px;padding:6px 12px;border-radius:8px;border:none;cursor:pointer;background:#f3f4f6;color:#374151}
.card .actions button.fav{background:#fef3c7;color:#92400e}
.knowledge-section{margin-bottom:16px}
.knowledge-section h3{font-size:15px;color:#2563eb;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #e5e7eb}
.knowledge-item{background:#fff;border-radius:10px;padding:12px;margin-bottom:8px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.knowledge-item .ki-title{font-size:13px;font-weight:600;margin-bottom:4px}
.knowledge-item .ki-what{font-size:12px;color:#374151;margin-bottom:2px}
.knowledge-item .ki-meta{font-size:10px;color:#9ca3af}
.detail{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:14px;line-height:1.8}
.detail h1{font-size:20px;margin-bottom:16px}
.detail h2{font-size:16px;color:#2563eb;margin:24px 0 10px;border-bottom:1px solid #e5e7eb;padding-bottom:4px}
.detail h3{font-size:14px;color:#374151;margin:16px 0 8px}
.detail h4{font-size:13px;margin:12px 0 6px}
.detail p{margin:6px 0}
.detail ul{margin:6px 0 6px 20px}
.detail li{margin:2px 0}
.detail a{color:#2563eb}
.detail hr{border:0;border-top:1px solid #e5e7eb;margin:16px 0}
.detail table{border-collapse:collapse;width:100%;margin:10px 0;font-size:12px}
.detail th,.detail td{border:1px solid #d1d5db;padding:6px 10px;text-align:left}
.detail th{background:#f3f4f6}
.detail blockquote{border-left:3px solid #2563eb;padding:4px 12px;margin:8px 0;background:#f8fafc;color:#64748b;font-size:13px}
.detail pre{background:#f1f5f9;padding:10px 14px;border-radius:6px;overflow-x:auto;font-size:12px}
.detail code{font-size:12px;background:#f1f5f9;padding:1px 4px;border-radius:3px}
.detail pre code{background:none;padding:0}
.back-btn{display:inline-flex;align-items:center;gap:4px;font-size:13px;color:#2563eb;cursor:pointer;border:none;background:none;margin-bottom:12px}
.search-bar{display:flex;gap:8px;margin-bottom:12px}
.search-bar input{flex:1;padding:10px 14px;border-radius:10px;border:1px solid #d1d5db;font-size:14px;outline:none}
.search-bar input:focus{border-color:#2563eb}
.kb-filter{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px}
.kb-filter button{font-size:11px;padding:4px 10px;border-radius:12px;border:1px solid #d1d5db;background:#fff;cursor:pointer}
.kb-filter button.active{background:#2563eb;color:#fff;border-color:#2563eb}
.glossary-grid{display:flex;flex-wrap:wrap;gap:10px}
.glossary-card{background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 2px rgba(0,0,0,.06);cursor:pointer;flex:1 1 calc(50% - 5px);min-width:140px;max-width:calc(50% - 5px)}
.glossary-card:active{opacity:.7}
.glossary-card .gc-title{font-size:13px;font-weight:600;color:#1e40af;margin-bottom:4px}
.glossary-card .gc-sub{font-size:10px;color:#9ca3af}
.glossary-card .gc-preview{font-size:11px;color:#6b7280;margin-top:4px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
@media(min-width:600px){.glossary-card{flex:1 1 calc(33% - 7px);max-width:calc(33% - 7px)}}

</style>
</head>
<body>

<div class="header"><h1>🤖 AI Weekly</h1></div>

<div class="page active" id="page-list">
<div class="search-bar"><input type="text" id="search" placeholder="Search reports..." oninput="renderList()"></div>
<div id="report-list"></div>
</div>

<div class="page" id="page-detail">
<button class="back-btn" onclick="showPage('list')">&larr; Back</button>
<div class="detail" id="detail-content"></div>
</div>

<div class="page" id="page-kb">
<div class="kb-filter" id="kb-filter"></div>
<div id="kb-content"></div>
</div>

<div class="page" id="page-kb-detail">
<button class="back-btn" onclick="showPage('kb')">&larr; Back</button>
<div class="detail" id="kb-detail-content"></div>
</div>

<div class="page" id="page-glossary">
<div class="search-bar"><input type="text" id="glossary-search" placeholder="Search terms..." oninput="renderGlossary()"></div>
<div id="glossary-grid"></div>
</div>

<div class="page" id="page-glossary-detail">
<button class="back-btn" onclick="showPage('glossary')">&larr; Back</button>
<div class="detail" id="glossary-detail-content"></div>
</div>

<div class="tab-bar">
<button class="tab active" data-page="list" onclick="showPage('list')">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
<span>Reports</span>
</button>
<button class="tab" data-page="kb" onclick="showPage('kb')">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
<span>Knowledge</span>
</button>
<button class="tab" data-page="glossary" onclick="showPage('glossary');renderGlossary()">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
<span>Glossary</span>
</button>
</div>

<script>
var REPORTS = __REPORTS__;
var KB = __KNOWLEDGE__;
var GLOSSARY = __GLOSSARY__;
var favs = JSON.parse(localStorage.getItem('aiweekly_favs') || '{}');

function showPage(name){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active')});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});
  var page = document.getElementById('page-'+name);
  if(page) page.classList.add('active');
  var tab = document.querySelector('[data-page="'+name+'"]');
  if(tab) tab.classList.add('active');
  if(name==='kb') renderKB('all');
  if(name==='list') renderList();
  if(name==='glossary') renderGlossary();
}

function renderList(){
  var q = (document.getElementById('search').value||'').toLowerCase();
  var html = '';
  var filtered = REPORTS.filter(function(r){
    if(!q) return true;
    return (r.title+r.summary+r.keywords).toLowerCase().indexOf(q)>=0;
  });
  filtered.forEach(function(r){
    var isFav = favs[r.id];
    var tags = (r.keywords||'').split(/[#\s]+/).filter(Boolean).slice(0,6);
    html += '<div class="card">';
    html += '<h3>'+r.title+'</h3>';
    html += '<div class="date">'+r.period+'</div>';
    html += '<div class="summary">'+r.summary+'</div>';
    if(tags.length) html += '<div class="tags">'+tags.map(function(t){return '<span class="tag">#'+t+'</span>'}).join('')+'</div>';
    html += '<div class="actions">';
    html += '<button onclick="openDetail(\''+r.id+'\')">Read</button>';
    html += '<button class="'+(isFav?'fav':'')+'" onclick="toggleFav(\''+r.id+'\')">'+(isFav?'★ Saved':'☆ Save')+'</button>';
    html += '</div></div>';
  });
  if(!filtered.length) html = '<div class="card" style="text-align:center;color:#9ca3af;padding:40px">No reports yet</div>';
  document.getElementById('report-list').innerHTML = html;
}

function openDetail(id){
  var r = REPORTS.find(function(x){return x.id===id});
  if(!r) return;
  document.getElementById('detail-content').innerHTML = '<h1>'+r.title+'</h1><div class="date">'+r.period+'</div>'+r.body;
  showPage('detail');
  window.scrollTo(0,0);
}

function toggleFav(id){
  favs[id] = !favs[id];
  localStorage.setItem('aiweekly_favs', JSON.stringify(favs));
  renderList();
}

function renderKB(filter){
  var subs = {};
  var allSubs = [];
  KB.forEach(function(item){
    var key = item.section + ' \u203a ' + item.sub;
    if(!subs[key]){ subs[key] = []; allSubs.push(key); }
    subs[key].push(item);
  });

  var fhtml = '<button class="'+(filter==='all'?'active':'')+'" onclick="renderKB(\'all\')">All</button>';
  allSubs.forEach(function(s){
    var label = s.split(' \u203a ').pop() || s;
    fhtml += '<button class="'+(filter===s?'active':'')+'" onclick="renderKB(\''+s.replace(/'/g,"\\'")+'\')">'+label+'</button>';
  });
  document.getElementById('kb-filter').innerHTML = fhtml;

  var html = '';
  allSubs.forEach(function(key){
    if(filter!=='all' && filter!==key) return;
    var items = subs[key];
    html += '<div class="knowledge-section"><h3>'+key+' ('+items.length+')</h3>';
    items.forEach(function(item){
      var date = '';
      REPORTS.forEach(function(r){
        if(r.body.indexOf(item.title)>=0) date = r.date;
      });
      html += '<div class="knowledge-item" onclick="openKbDetail(''+item.title.replace(/'/g,'\'')+'')">';
      html += '<div class="ki-title">'+item.title+'</div>';
      html += '<div class="ki-what">'+(item.what||item.why||'').substring(0,150)+'</div>';
      html += '<div class="ki-meta">'+item.source+(date?' \u00b7 '+date:'')+'</div>';
      html += '</div>';
    });
    html += '</div>';
  });
  document.getElementById('kb-content').innerHTML = html || '<div class="card" style="text-align:center;color:#9ca3af;padding:40px">No knowledge entries yet</div>';
}

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

        # Generate glossary from knowledge items
    glossary = []
    seen_terms = set()
    for k in all_knowledge:
        term = k["title"]
        # Simplify long titles
        if "：" in term:
            term = term.split("：")[0].split(":")[0].strip()
        if len(term) > 50:
            term = term[:47] + "..."
        key = term.lower()
        if key not in seen_terms:
            seen_terms.add(key)
            glossary.append({
                "term": term,
                "section": k.get("section", ""),
                "sub": k.get("sub", ""),
                "what": k.get("what", ""),
                "why": k.get("why", ""),
                "source": k.get("source", ""),
                "link": k.get("link", ""),
            })

    html = HTML_TPL.replace("__REPORTS__", json.dumps(reports, ensure_ascii=False))
    html = html.replace("__KNOWLEDGE__", json.dumps(all_knowledge, ensure_ascii=False))
    html = html.replace("__GLOSSARY__", json.dumps(glossary, ensure_ascii=False))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"App built: {out_path}  ({len(reports)} reports, {len(all_knowledge)} knowledge, {len(glossary)} glossary terms)")


if __name__ == "__main__":
    main()
