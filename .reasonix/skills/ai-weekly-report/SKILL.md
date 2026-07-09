---
name: ai-weekly-report
description: Use when the user wants an AI weekly report covering technology advances and company news from 8 sources (GitHub, HF Papers, TechCrunch, MIT TR, 量子位, 机器之心, 36氪, 雷锋网). Triggered by "AI 周报", "weekly AI report", "本周 AI 动态".
---

# AI Weekly Report

Automatically scrape 8 authoritative AI news sources (4 overseas + 4 domestic China), analyze, and generate a structured Markdown weekly report covering both AI technology advances and AI company news.

## When to Use

Use when the user:
- Says "出本周 AI 周报", "weekly AI report", "AI 周报", or similar
- Wants a consolidated weekly briefing on AI progress
- Asks about "this week in AI"

## Data Sources (8 total)

### Overseas — Technology Advances

| # | Source | URL | Command |
|---|--------|-----|---------|
| 1 | GitHub Trending (weekly) | `https://github.com/trending?since=weekly` | `scrapling extract get "<URL>" temp_gh.md --ai-targeted --timeout 30` |
| 2 | Hugging Face Daily Papers | `https://huggingface.co/papers` | `scrapling extract fetch "<URL>" temp_hf.md --ai-targeted --timeout 60000 --network-idle` |

### Overseas — Company News

| # | Source | URL | Command |
|---|--------|-----|---------|
| 3 | TechCrunch AI | `https://techcrunch.com/category/artificial-intelligence/` | `scrapling extract get "<URL>" temp_tc.md --ai-targeted --timeout 30` |
| 4 | MIT Technology Review AI | `https://www.technologyreview.com/topic/artificial-intelligence/` | `scrapling extract fetch "<URL>" temp_mit.md --ai-targeted --timeout 60000 --network-idle` |

### 🇨🇳 Domestic — Technology Advances

| # | Source | URL | Command |
|---|--------|-----|---------|
| 5 | 量子位 (QbitAI) | `https://www.qbitai.com/` | `scrapling extract get "<URL>" temp_qb.md --ai-targeted --timeout 30` |
| 6 | 机器之心 (Jiqi Zhixin) | `https://www.jiqizhixin.com/articles` | `scrapling extract fetch "<URL>" temp_jq.md --ai-targeted --timeout 60000 --network-idle` |

### 🇨🇳 Domestic — Company News

| # | Source | URL | Command |
|---|--------|-----|---------|
| 7 | 36氪 AI | `https://36kr.com/information/AI/` | `scrapling extract get "<URL>" temp_36.md --ai-targeted --timeout 30` |
| 8 | 雷锋网 AI | `https://www.leiphone.com/category/ai` | `scrapling extract get "<URL>" temp_lf.md --ai-targeted --timeout 30` |

## Pipeline

### Step 1: Scrape All Sources

Run all 8 commands. Because GitHub Trending, Hugging Face, and the four domestic sources have no dependency, they can all run in parallel. MIT Tech Review needs `fetch`.

**Always start with `get`; escalate to `fetch` only if the output is empty or obviously incomplete.**

### Step 2: Read & Extract

Read each temp file. For each source, extract:
- **Title** of each article/repo/paper
- **One-line summary** (what happened)
- **Why it matters** (significance judgment)
- **Source link** (URL)

Filter criteria:
- **Must be AI-related** — skip purely general tech, non-AI hardware, etc.
- **Prefer items with community signal** (stars, upvotes, comments) over bare listings
- **De-duplicate** — if multiple sources cover the same story (e.g. Grok 4.5 appeared on TechCrunch, 量子位, 36氪), merge into one entry with multiple source links

### Step 3: Classify & Organize (大类套小类)

**Curate first**: from all extracted items, pick only the **10-15 most important** ones. Selection criteria: community signal (stars/upvotes), cross-source coverage, strategic significance, novelty.

Sort into a three-level hierarchy:

**1. 🔬 AI 技术前沿**

| 子类 | 涵盖内容 |
|------|----------|
| **大模型与架构** | New LLM releases, training techniques, MoE, distillation, scaling laws |
| **具身智能与世界模型** | VLA, world models, robot foundation models, sim-to-real |
| **开源与工具** | Open-source releases, developer tools, programming languages, benchmarks |
| **学术前沿** | Top conference papers, best paper awards, emerging research directions |

**2. 🏢 AI 公司动态**

| 子类 | 涵盖内容 |
|------|----------|
| **资本与估值** | Funding rounds, IPOs, M&A, valuations, investment trends |
| **产品与发布** | Product launches, feature updates, model releases |
| **战略与治理** | Policy changes, regulatory actions, talent moves, org restructuring |
| **行业趋势** | Cross-company patterns, layoff waves, market shifts |

**3. 🌏 国内视角**

| 子类 | 涵盖内容 |
|------|----------|
| **大厂动向** | BAT/ByteDance/Meituan AI strategy, product moves, talent changes |
| **创业与融资** | Domestic startup funding, unicorn updates, industry applications |
| **学术与人才** | Chinese papers at top venues, talent competition, education |
| **政策与生态** | Government AI policy, industry alliances, open-source ecosystem |

**4. 📊 本周趋势**
- 2-3 paragraphs synthesizing cross-cutting themes, with specific data points

Each item must have **What → Why → Impact** structure (see Step 4 template).

### Step 4: Generate Report

Write the report to `weekly-reports/ai-weekly-YYYY-MM-DD.md`. Must use **大类套小类** and **精选深挖** (10-15 items total, each with 3-5 sentence depth).

```markdown
---
title: "AI 周报 YYYY-MM-DD"
date: "YYYY-MM-DD"
period: "YYYY年M月D日 – YYYY年M月D日"
sources: [GitHub Trending, Hugging Face Papers, TechCrunch, MIT Tech Review, 量子位, 机器之心, 36氪, 雷锋网]
---

# 🤖 AI 周报 | YYYY年M月D日 – YYYY年M月D日

## 📊 本周趋势

<2-3 paragraphs, each on a major cross-cutting theme with concrete examples and data>

---

## 🔬 AI 技术前沿

### 大模型与架构

#### <Item Title>
- **发生了什么**：<3-5 sentences: who, what, when, numbers, technical details>
- **为什么重要**：<2-3 sentences: context, competitive landscape, implications>
- **来源**：<Source>
- **链接**：<URL>

### 具身智能与世界模型

...

### 开源与工具

...

### 学术前沿

...

---

## 🏢 AI 公司动态

### 资本与估值
...

### 产品与发布
...

### 战略与治理
...

### 行业趋势
...

---

## 🌏 国内视角

### 大厂动向
...

### 创业与融资
...

### 学术与人才
...

### 政策与生态
...

---

## 📋 本周数据速览

| 指标 | 数据 |
|------|------|
| GitHub 最热 AI 项目 | <top repo> (⭐ +X) |
| HuggingFace 最热论文 | <top paper> |
| 国内最热事件 | <top domestic story> |
| 本周关键词 | #tag1 #tag2 #tag3 |
```
**Skip any sub-category that has zero notable items this week.**

### Step 5: Convert to PDF

Convert the Markdown report to a clean, readable PDF:

```bash
python scripts/md_to_pdf.py weekly-reports/ai-weekly-YYYY-MM-DD.md
```

### Step 6: Build Mobile App

Regenerate the self-contained HTML app (viewable on phone via cloud sync or browser):

```bash
python scripts/build_app.py weekly-reports/app.html
```

Generates a single-file PWA-style app with three tabs: Reports list, Report detail, Knowledge base (all items aggregated and categorized across all reports).

### Step 7: Send Email with PDF

Email the PDF report:

```bash
python scripts/send_email.py weekly-reports/ai-weekly-YYYY-MM-DD.pdf "AI Weekly Report YYYY-MM-DD"
```

**Prerequisite**: SMTP auth code must be set in config/email.json.

### Step 8: Push to Feishu

After the report is written (and email sent if configured), push a summary card to Feishu group chat:

```bash
python scripts/feishu_push.py weekly-reports/ai-weekly-YYYY-MM-DD.md
```

The script:
- Reads the generated Markdown report
- Extracts title, keywords, trends, top GitHub repo, top paper
- Builds an interactive Feishu card with a summary + full report path
- If email was also sent, note it in the card footer (e.g. "PDF sent to yjw839627486@163.com")
- POSTs to the webhook URL in `config/feishu.json`

**Prerequisite**: The user must configure `config/feishu.json` with a valid webhook URL. If not configured, skip this step with a reminder.

### Step 8: Cleanup

Delete ALL temp files: `rm -f temp_gh.md temp_hf.md temp_tc.md temp_mit.md temp_qb.md temp_jq.md temp_36.md temp_lf.md`

## Content Guidelines

- **精选深挖** — pick only 10-15 most important items total across all categories; skip filler
- **每条有深度** — minimum 3-5 sentences for "what happened", 2-3 sentences for "why it matters"
- **大类套小类** — always use sub-category headings; skip sub-categories that have zero items
- **Title in Chinese**, technical terms kept in original English
- **Summary must be factual** — never fabricate details not in the source
- **De-duplicate across sources** — same story from multiple outlets = one entry with multiple links
- **If a source returns nothing useful**, skip it rather than padding

## Email Setup

1. Login to 163 email → Settings → POP3/SMTP/IMAP
2. Enable SMTP service, get the authorization code
3. Paste into `config/email.json`:
```json
{
  "smtp_server": "smtp.163.com",
  "smtp_port": 465,
  "sender": "yjw839627486@163.com",
  "password": "YOUR_SMTP_AUTH_CODE",
  "receiver": "yjw839627486@163.com",
  "enabled": true
}
```
4. Set `enabled: false` to temporarily disable email sending

## Feishu Push Setup

1. In Feishu group → Settings → Group Bot → Add Custom Bot
2. Copy the Webhook URL
3. Paste into `config/feishu.json`:
```json
{
  "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxx",
  "enabled": true
}
```
4. Set `enabled: false` to temporarily disable push

## Quick Reference

| Step | Action | Parallel? |
|------|--------|-----------|
| 1 | Scrape 8 sources | ✅ All 8 in parallel |
| 2 | Read & extract key items | Sequential read, parallel analysis |
| 3 | De-duplicate & classify | — |
| 4 | Write structured report (.md) | — |
| 5 | Convert to PDF (styled) | — |
| 6 | Send email with PDF | — |
| 7 | Push summary card to Feishu | — |
| 8 | Cleanup temp files | — |

## Escalation Policy

| Symptom | Action |
|---------|--------|
| `get` returns <20 lines of real content | Re-run with `fetch --network-idle` |
| `fetch` also returns little | Try `stealthy-fetch --solve-cloudflare` |
| Source consistently fails | Skip and note in report |
| File already exists | Ask user before overwriting |
