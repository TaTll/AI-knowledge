#!/usr/bin/env python3
"""Convert AI Weekly Markdown report to a clean, readable PDF via Chrome headless."""

import sys, re, os, subprocess, tempfile
from pathlib import Path

CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"


def parse_frontmatter(content):
    result = {}
    for key in ["title", "period", "date"]:
        m = re.search(rf'{key}:\s*"(.+?)"', content)
        if m: result[key] = m.group(1)
    return result


def md_to_html(md_path):
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    # Split frontmatter
    body = raw
    fm = {}
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        fm = parse_frontmatter(parts[1]) if len(parts) > 1 else {}
        body = parts[2] if len(parts) > 2 else raw

    lines = body.split("\n")
    html_lines = []
    in_code = False
    in_table = False
    in_list = False
    in_quote = False

    for line in lines:
        stripped = line.strip()

        # Code block toggle
        if stripped.startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                html_lines.append('<pre><code>')
                in_code = True
            continue

        if in_code:
            html_lines.append(_escape(line))
            continue

        # Horizontal rule
        if stripped == "---":
            html_lines.append("<hr>")
            continue

        # Table
        if "|" in stripped and stripped.startswith("|"):
            if not in_table:
                in_table = True
                html_lines.append('<table>')
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            is_sep = all(re.match(r"^[-:]+$", c) for c in cells)
            if is_sep:
                continue
            tag = "th" if in_table and html_lines and html_lines[-1] == '<table>' else "td"
            html_lines.append("<tr>" + "".join(f"<{tag}>{_escape(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        elif in_table:
            html_lines.append("</table>")
            in_table = False
            in_list = False

        # Headings
        if stripped.startswith("# "):
            html_lines.append(f'<h1>{_inline(stripped[2:])}</h1>')
            in_list = False
            continue
        if stripped.startswith("## "):
            html_lines.append(f'<h2>{_inline(stripped[2:])}</h2>')
            in_list = False
            continue
        if stripped.startswith("### "):
            html_lines.append(f'<h3>{_inline(stripped[4:])}</h3>')
            in_list = False
            continue
        if stripped.startswith("#### "):
            html_lines.append(f'<h4>{_inline(stripped[5:])}</h4>')
            in_list = False
            continue

        # Blockquote
        if stripped.startswith("> "):
            if not in_quote:
                html_lines.append("<blockquote>")
                in_quote = True
            html_lines.append(f'<p>{_inline(stripped[2:])}</p>')
            continue
        elif in_quote:
            html_lines.append("</blockquote>")
            in_quote = False

        # Unordered list
        if re.match(r"^\s*[-*]\s+", stripped):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            text = re.sub(r"^\s*[-*]\s+", "", stripped)
            html_lines.append(f"<li>{_inline(text)}</li>")
            continue
        elif in_list and stripped == "":
            html_lines.append("</ul>")
            in_list = False
            continue
        elif in_list:
            html_lines.append("</ul>")
            in_list = False

        # Paragraph
        if stripped:
            html_lines.append(f"<p>{_inline(stripped)}</p>")
        else:
            html_lines.append("")

    # Flush
    if in_table: html_lines.append("</table>")
    if in_list: html_lines.append("</ul>")
    if in_quote: html_lines.append("</blockquote>")

    title = fm.get("title", "AI Weekly Report")
    period = fm.get("period", "")
    date_str = fm.get("date", "")

    header = ""
    if period or date_str:
        header = '<div class="header-meta">'
        if period: header += f'<span>{period}</span>'
        if date_str: header += f'<span>Generated: {date_str}</span>'
        header += '</div>'

    body_html = "\n".join(html_lines)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Microsoft YaHei', 'PingFang SC', 'Noto Sans SC', 'Segoe UI', sans-serif;
    font-size: 12pt; line-height: 1.8; color: #1a1a1a;
    max-width: 750px; margin: 0 auto; padding: 50px 40px;
    background: #fff;
}}
.header-meta {{ font-size: 9pt; color: #888; margin-bottom: 24px; }}
.header-meta span {{ margin-right: 18px; }}
h1 {{ font-size: 24pt; font-weight: 800; margin: 30px 0 16px; color: #111; border-bottom: 3px solid #2563eb; padding-bottom: 8px; }}
h2 {{ font-size: 16pt; font-weight: 700; margin: 28px 0 12px; color: #2563eb; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
h3 {{ font-size: 13pt; font-weight: 700; margin: 20px 0 8px; color: #374151; }}
h4 {{ font-size: 12pt; font-weight: 700; margin: 16px 0 6px; color: #1a1a1a; }}
p {{ margin: 6px 0 10px; text-align: justify; }}
ul {{ margin: 8px 0 12px 24px; }}
li {{ margin: 3px 0; }}
strong {{ color: #111; }}
a {{ color: #2563eb; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
hr {{ border: 0; border-top: 1px solid #e5e7eb; margin: 20px 0; }}
blockquote {{
    border-left: 4px solid #2563eb; padding: 6px 16px; margin: 12px 0;
    background: #f8fafc; color: #64748b; font-size: 11pt;
}}
blockquote p {{ margin: 4px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 11pt; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px 14px; text-align: left; }}
th {{ background: #f3f4f6; font-weight: 700; }}
pre {{ background: #f1f5f9; padding: 14px 18px; border-radius: 6px; overflow-x: auto; margin: 10px 0; font-size: 10pt; line-height: 1.5; }}
code {{ font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace; font-size: 10pt; }}
p code, li code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 3px; font-size: 10pt; }}
@page {{ size: A4; margin: 15mm; }}
@media print {{ body {{ padding: 0; max-width: none; }} }}
</style></head>
<body>
{header}
{body_html}
</body></html>"""


def _escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _inline(text):
    """Convert inline markdown to HTML"""
    t = _escape(text)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'!\[.*?\]\((.+?)\)', r'<img src="\1" style="max-width:100%">', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    # Plain URLs — but not already inside <a> or <img> tags
    t = re.sub(r'(?<!["=])(https?://[^\s)\]»，。；\u201c\u201d]+)', r'<a href="\1">\1</a>', t)
    return t


def html_to_pdf(html_path, pdf_path):
    abs_html = f"file:///{Path(html_path).resolve().as_posix()}"
    abs_pdf = str(Path(pdf_path).resolve())
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--print-to-pdf={abs_pdf}", "--no-pdf-header-footer", abs_html
    ], capture_output=True, timeout=60)
    if not Path(pdf_path).exists():
        raise RuntimeError("PDF generation failed")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/md_to_pdf.py <report.md> [output.pdf]")
        sys.exit(1)
    md_path = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) >= 3 else str(Path(md_path).with_suffix(".pdf"))
    if not Path(md_path).exists():
        print(f"[ERROR] File not found: {md_path}")
        sys.exit(1)
    if not Path(CHROME).exists():
        print(f"[ERROR] Chrome not found: {CHROME}")
        sys.exit(1)

    html = md_to_html(md_path)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    try:
        html_to_pdf(tmp, pdf_path)
        print(f"PDF generated: {pdf_path}")
    finally:
        os.unlink(tmp)


if __name__ == "__main__":
    main()
