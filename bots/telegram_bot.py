from __future__ import annotations

import os

import requests


def send_telegram(message: str) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"sent": False, "reason": "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not configured"}
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=15,
    )
    return {"sent": response.ok, "status_code": response.status_code}

