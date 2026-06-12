from __future__ import annotations

import os

import requests

from app.env import load_env_file


def send_discord(message: str) -> dict:
    load_env_file()
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return {"sent": False, "reason": "DISCORD_WEBHOOK_URL is not configured"}
    response = requests.post(webhook_url, json={"content": message}, timeout=15)
    return {"sent": response.ok, "status_code": response.status_code}
