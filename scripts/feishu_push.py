#!/usr/bin/env python3
"""推送 AI 周报到飞书群机器人（卡片摘要 + 完整报告路径）"""

import json
import sys
import re
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] Missing requests library. Run: pip install requests")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "feishu.json"


def load_config():
    if not CONFIG_PATH.exists():
        print(f"[ERROR] Config file not found: {CONFIG_PATH}")
        print("请复制 config/feishu.json.example 并填写你的飞书 Webhook URL")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def parse_report(filepath: str) -> dict:
    """从周报 Markdown 中提取摘要信息"""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # 标题
    title = "AI 周报"
    m = re.search(r"# 🤖 AI 周报 \| (.+)", content)
    if m:
        title = m.group(1).strip()

    # 关键词
    keywords = ""
    m = re.search(r"本周关键词[：:]\s*(.+)", content)
    if m:
        keywords = m.group(1).strip()

    # 趋势段落
    trends = ""
    m = re.search(r"## 📊 本周趋势\n\n(.+?)(?=\n---)", content, re.DOTALL)
    if m:
        raw = m.group(1).strip()
        trends = raw[:400] + ("..." if len(raw) > 400 else "")

    # GitHub 最热
    gh = ""
    m = re.search(r"GitHub 最热 AI 项目\s*\|\s*(.+?)\s*\|", content)
    if m:
        gh = m.group(1).strip()

    # HF 最热论文
    hf = ""
    m = re.search(r"HuggingFace 最热论文\s*\|\s*(.+?)\s*\|", content)
    if m:
        hf = m.group(1).strip()

    return {
        "title": title,
        "keywords": keywords,
        "trends": trends,
        "top_github": gh,
        "top_paper": hf,
    }


def build_card(info: dict, filepath: str) -> dict:
    """构建飞书交互式消息卡片"""
    fields = []
    if info["top_github"]:
        fields.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": f"🔥 **GitHub 最热**：{info['top_github']}"}}
        )
    if info["top_paper"]:
        fields.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": f"📄 **最热论文**：{info['top_paper']}"}}
        )
    if info["keywords"]:
        fields.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": f"🏷️ **关键词**：{info['keywords']}"}}
        )

    elements = []
    if info["trends"]:
        elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**📊 本周趋势**\n{info['trends']}"}}
        )
        elements.append({"tag": "hr"})

    elements.extend(fields)

    elements.append({"tag": "hr"})
    elements.append(
        {"tag": "div", "text": {"tag": "lark_md", "content": f"📁 完整报告：`{filepath}`"}}
    )
    elements.append(
        {
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": "🤖 AI Weekly Report · 自动生成"}],
        }
    )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🤖 AI 周报 | {info['title']}"},
                "template": "blue",
            },
            "elements": elements,
        },
    }


def push(webhook_url: str, payload: dict):
    resp = requests.post(webhook_url, json=payload, timeout=15)
    resp.raise_for_status()
    result = resp.json()
    code = result.get("code", -1)
    if code != 0:
        raise Exception(f"飞书返回错误 code={code}: {result.get('msg', '未知错误')}")
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/feishu_push.py <weekly-report.md>")
        sys.exit(1)

    report_path = sys.argv[1]
    if not Path(report_path).exists():
        print(f"[ERROR] File not found: {report_path}")
        sys.exit(1)

    config = load_config()
    if not config.get("enabled", True):
        print("[SKIP] Feishu push disabled in config")
        return

    webhook_url = config.get("webhook_url", "")
    if not webhook_url or "YOUR_WEBHOOK_TOKEN" in webhook_url:
        print("[ERROR] Feishu Webhook URL not configured in config/feishu.json")
        sys.exit(1)

    info = parse_report(report_path)
    card = build_card(info, report_path)
    push(webhook_url, card)
    print(f"Feishu push OK: {info['title']}")


if __name__ == "__main__":
    main()
