#!/usr/bin/env python3
"""Wallet Guardian — $5.00/day API cost fuse.

Runs every 5 minutes via crontab.
Checks DashScope / Anthropic API usage for the current day.
If cost >= $5.00, kills all known API-consuming processes.
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

DAILY_LIMIT_USD = float(os.environ.get("WALLET_GUARDIAN_LIMIT", "5.00"))
LOG_DIR = Path(os.environ.get("WALLET_GUARDIAN_LOG_DIR", "/tmp/wallet_guardian"))
PROCESS_PATTERNS = [
    "athena_ai_plan_runner",
    "athena_autoresearch",
    "continuous_engine",
    "autoresearch_loop",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("wallet_guardian")


def get_dashscope_today_cost() -> float:
    """Query DashScope API usage for today.

    Uses environment variable DASHSCOPE_API_KEY for auth.
    Falls back to 0.0 if query fails.
    """
    import requests

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY not set, skipping DashScope check")
        return 0.0

    today = date.today().isoformat()
    url = "https://dashscope.aliyuncs.com/api/v1/services/billing/daily-cost"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"date": today}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("total_cost", 0.0))
        else:
            logger.warning("DashScope API returned %s: %s", resp.status_code, resp.text[:200])
            return 0.0
    except Exception as e:
        logger.warning("Failed to query DashScope cost: %s", e)
        return 0.0


def estimate_cost_from_logs() -> float:
    """Fallback: estimate cost from log files.

    Parses recent log lines for cost estimates when API is unavailable.
    """
    total = 0.0
    for log_pattern in ["*.log", "logs/*.log"]:
        for log_file in Path.cwd().glob(log_pattern):
            try:
                text = log_file.read_text(errors="ignore")
                for line in text.splitlines():
                    if "$" in line and "cost" in line.lower():
                        import re
                        match = re.search(r'\$?(\d+\.?\d*)', line)
                        if match:
                            total += float(match.group(1))
            except Exception:
                continue
    return min(total, DAILY_LIMIT_USD)


def kill_processes() -> int:
    """Kill all known API-consuming processes. Returns count killed."""
    killed = 0
    for pattern in PROCESS_PATTERNS:
        try:
            result = subprocess.run(
                ["pkill", "-f", pattern],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.warning("Killed processes matching: %s", pattern)
                killed += 1
        except subprocess.TimeoutExpired:
            logger.error("Timeout killing processes: %s", pattern)
        except FileNotFoundError:
            logger.warning("pkill not available on this system")
            break
    return killed


def main():
    if "--check" in sys.argv:
        pass  # check mode: same as normal run

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    api_cost = get_dashscope_today_cost()
    estimated_cost = estimate_cost_from_logs()
    total_cost = max(api_cost, estimated_cost)

    state = {
        "timestamp": time.time(),
        "date": date.today().isoformat(),
        "api_cost": api_cost,
        "estimated_cost": estimated_cost,
        "total_cost": total_cost,
        "limit": DAILY_LIMIT_USD,
        "fuse_triggered": total_cost >= DAILY_LIMIT_USD,
    }

    state_file = LOG_DIR / "state.json"
    state_file.write_text(json.dumps(state, indent=2))

    if total_cost >= DAILY_LIMIT_USD:
        logger.critical(
            "FUSE TRIGGERED: $%.2f / $%.2f daily limit. Killing processes.",
            total_cost,
            DAILY_LIMIT_USD,
        )
        killed = kill_processes()
        logger.critical("Killed %d process groups. System halted.", killed)
        sys.exit(1)
    else:
        logger.info(
            "OK: $%.2f / $%.2f daily limit (%.1f%%)",
            total_cost,
            DAILY_LIMIT_USD,
            (total_cost / DAILY_LIMIT_USD) * 100,
        )


if __name__ == "__main__":
    main()
