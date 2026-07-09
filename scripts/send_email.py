#!/usr/bin/env python3
"""Send AI weekly report PDF via 163 email"""

import json
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "email.json"


def load_config():
    if not CONFIG_PATH.exists():
        print(f"[ERROR] Config file not found: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def send_email(config: dict, pdf_path: str, subject: str):
    msg = MIMEMultipart()
    msg["From"] = config["sender"]
    msg["To"] = config["receiver"]
    msg["Subject"] = subject

    body = f"""<html><body style="font-family: 'Microsoft YaHei', sans-serif;">
<h2>AI Weekly Report</h2>
<p>本周 AI 周报已生成，详见 PDF 附件。</p>
<p>报告路径：<code>{pdf_path}</code></p>
<hr>
<p style="color: #6b7280; font-size: 12px;">AI Weekly Report · Auto-generated</p>
</body></html>"""
    msg.attach(MIMEText(body, "html", "utf-8"))

    with open(pdf_path, "rb") as f:
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="{Path(pdf_path).name}"',
        )
        msg.attach(attachment)

    with smtplib.SMTP_SSL(config["smtp_server"], config["smtp_port"]) as server:
        server.login(config["sender"], config["password"])
        server.sendmail(config["sender"], config["receiver"], msg.as_string())


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/send_email.py <report.pdf> [subject]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    subject = sys.argv[2] if len(sys.argv) >= 3 else "AI Weekly Report"

    if not Path(pdf_path).exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)

    config = load_config()
    if not config.get("enabled", True):
        print("[SKIP] Email sending disabled in config")
        return

    password = config.get("password", "")
    if not password or "YOUR_SMTP_AUTH_CODE" in password:
        print("[ERROR] SMTP auth code not configured in config/email.json")
        sys.exit(1)

    send_email(config, pdf_path, subject)
    print(f"Email sent: {subject} -> {config['receiver']}")


if __name__ == "__main__":
    main()
