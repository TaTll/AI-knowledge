---
name: url-to-knowledge
description: Use when the user wants to convert web page URLs into structured Markdown knowledge base files. Triggered by "save this article", "归档这个网页", "create knowledge base from URL", or sharing a URL to save.
---

# URL to Knowledge Base

Convert web pages into structured, well-organized Markdown knowledge base files. A lightweight 4-step pipeline triggered by a single command.

## When to Use

Use when the user:
- Shares one or more URLs and asks to "save", "convert to notes", "create knowledge base entry", or "归档"
- Wants web content distilled into structured Markdown files
- Asks to build a personal knowledge base from web sources

## Pipeline (4 Steps)

### Step 1: Collect URLs
Ask the user for the URL(s) if not already provided. Also ask:
- Any specific focus/topic for the extraction?
- Target directory? (default: `knowledge-base/`)
- Single file or separate files per URL?

### Step 2: Scrape with Scrapling

For each URL, choose the right command based on site complexity:

| Site type | Command |
|-----------|---------|
| Simple blog/article | `scrapling extract get "<URL>" temp_page.md --ai-targeted` |
| JavaScript-heavy SPA | `scrapling extract fetch "<URL>" temp_page.md --network-idle --ai-targeted` |
| Anti-bot protected | `scrapling extract stealthy-fetch "<URL>" temp_page.md --solve-cloudflare --ai-targeted` |

**Rule**: Start with `get`. If the output looks incomplete, escalate to `fetch`, then `stealthy-fetch`.

Always use `--ai-targeted` to strip noise (ads, nav, sidebars). Output to a temp file like `temp_page.md`.

### Step 3: Read & Analyze

Read the scraped Markdown file. Then:

1. **Identify the core topic** — what is this page fundamentally about?
2. **Extract key points** — main arguments, data, conclusions
3. **Identify structure** — natural sections, hierarchy
4. **Note metadata** — title, author, date, source URL

### Step 4: Generate Knowledge Base File

Write a polished Markdown file to the target directory. Follow this structure:

```markdown
---
title: "<Page Title>"
source: "<URL>"
date_scraped: "<YYYY-MM-DD>"
tags: [tag1, tag2]
---

# <Title>

## Overview
<1-2 sentence summary>

## Key Points
- Point 1
- Point 2

## Detailed Notes
### <Section 1>
<Content>

### <Section 2>
<Content>

## References
- Source: <URL>
```

**Rules**:
- Preserve factual accuracy — don't invent content not in the source
- Use Chinese for commentary if the user communicates in Chinese; keep technical terms in original
- Organize hierarchically: Overview → Key Points → Detailed Notes
- Add relevant tags for future searchability
- File naming: kebab-case based on title, e.g. `knowledge-base/react-19-new-features.md`

### Step 5: Cleanup

Delete temp files (`temp_page.md`, etc.) after successful write.

## Quick Reference

| Step | Action | Tool |
|------|--------|------|
| 1 | Collect URLs & preferences | ask / conversation |
| 2 | Scrape content | bash: `scrapling extract get/fetch` |
| 3 | Read & analyze | read_file |
| 4 | Write knowledge base | write_file |
| 5 | Cleanup temp files | bash: `rm temp_page.md` |

## Common Mistakes

- **Don't skip `--ai-targeted`** — raw HTML dump wastes tokens and produces poor notes
- **Don't use `stealthy-fetch` unnecessarily** — it's slower; escalate only when needed
- **Don't alter facts** — knowledge base must reflect the source, not your interpretation
- **Don't create one giant file for multiple unrelated URLs** — split by topic
- **Always ask before writing** if the target file already exists

## Guardrails

- Only scrape publicly accessible content
- Respect robots.txt — Scrapling does this by default in spider mode
- Never scrape content behind authentication without explicit permission
- Delete all temp files when done
