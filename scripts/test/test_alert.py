#!/usr/bin/env python3
"""test_alert.py — Send test alert via email and/or Slack from monitoring_config.yaml."""

import os
import smtplib
import ssl
import sys
from email.mime.text import MIMEText
from pathlib import Path

import requests
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "monitoring_config.yaml"


def load_config():
    if not CONFIG_PATH.exists():
        print(f"FATAL: {CONFIG_PATH} not found", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(val: str) -> str:
    if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
        env_key = val[2:-1]
        return os.environ.get(env_key, val)
    return val


def test_email(cfg: dict) -> bool:
    email_cfg = cfg.get("email", {})
    smtp_server = email_cfg.get("smtp_server", "")
    smtp_port = email_cfg.get("smtp_port", 587)
    from_email = email_cfg.get("from_email", "")
    to_emails = email_cfg.get("to_emails", [])
    username = email_cfg.get("username", "")
    password = resolve(email_cfg.get("password", ""))
    use_tls = email_cfg.get("use_tls", True)
    subject_prefix = email_cfg.get("subject_prefix", "")

    if not password or password.startswith("${"):
        print("SKIP email: password not configured (env var not set)")
        return False

    msg = MIMEText("This is a test alert from OpenClaw monitoring system.\n\nTimestamp: test", _charset="utf-8")
    msg["Subject"] = f"{subject_prefix}Test Alert"
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)

    try:
        if use_tls:
            with smtplib.SMTP(smtp_server, smtp_port) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(username, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as s:
                s.login(username, password)
                s.send_message(msg)
        print(f"OK email sent to {to_emails}")
        return True
    except Exception as e:
        print(f"FAIL email: {e}")
        return False


def test_slack(cfg: dict) -> bool:
    slack_cfg = cfg.get("slack", {})
    webhook_url = resolve(slack_cfg.get("webhook_url", ""))

    if not webhook_url or "T00000000" in webhook_url:
        print("SKIP slack: webhook URL is placeholder or not set")
        return False

    payload = {
        "channel": slack_cfg.get("channel", "#alerts"),
        "username": slack_cfg.get("username", "OpenClaw Monitor"),
        "icon_emoji": slack_cfg.get("icon_emoji", ":warning:"),
        "attachments": [{
            "color": slack_cfg.get("colors", {}).get("info", "#36A64F"),
            "title": "Test Alert from OpenClaw",
            "text": "This is a test alert. If you see this, the Slack channel is working.",
            "footer": "OpenClaw Test Alert System",
        }],
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("OK slack message sent")
            return True
        else:
            print(f"FAIL slack: HTTP {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"FAIL slack: {e}")
        return False


def main():
    cfg = load_config()
    ok_email = test_email(cfg)
    ok_slack = test_slack(cfg)
    if not ok_email and not ok_slack:
        print("No alerts sent. Configure credentials or set environment variables.")
        sys.exit(1)


if __name__ == "__main__":
    main()
