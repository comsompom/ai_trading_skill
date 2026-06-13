from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from telegram import Bot

from app.env import load_env_file

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_LIMIT = 1024


class TelegramPoster:
    """Handles posting to a Telegram chat or channel."""

    def __init__(self, token: str | None = None, channel_id: str | None = None):
        load_env_file()
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = _normalize_telegram_chat_id(
            channel_id or os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID")
        )
        if not self.token or not self.channel_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID or TELEGRAM_CHAT_ID are not configured")
        self.bot = Bot(token=self.token)

    async def post_message(self, message: str, image_path: str | None = None) -> dict:
        """Post a message to Telegram with an optional image."""
        try:
            if image_path:
                caption = _truncate_caption(message)
                with Path(image_path).open("rb") as photo:
                    await self.bot.send_photo(chat_id=self.channel_id, photo=photo, caption=caption)
                logger.info("Successfully posted image and message to Telegram: %s...", caption[:50])
            else:
                await self.bot.send_message(chat_id=self.channel_id, text=message)
                logger.info("Successfully posted to Telegram: %s...", message[:50])
            return {"sent": True, "platform": "Telegram"}
        except Exception as exc:
            logger.error("Failed to post to Telegram: %s", exc)
            return {"sent": False, "platform": "Telegram", "reason": str(exc)}


def send_telegram(message: str, image_path: str | None = None) -> dict:
    try:
        poster = TelegramPoster()
    except ValueError as exc:
        return {"sent": False, "platform": "Telegram", "reason": str(exc)}

    return asyncio.run(poster.post_message(message, image_path=image_path))


def _truncate_caption(message: str) -> str:
    if len(message) <= TELEGRAM_CAPTION_LIMIT:
        return message

    truncated_message = message[: TELEGRAM_CAPTION_LIMIT - 3]
    last_space = truncated_message.rfind(" ")
    if last_space > 900:
        return message[:last_space] + "..."
    return truncated_message + "..."


def _normalize_telegram_chat_id(chat_id: str | None) -> str | None:
    if chat_id is None:
        return None

    normalized = chat_id.strip()
    if normalized.startswith(("-", "@")):
        return normalized

    # Telegram private channel/supergroup ids are commonly copied without the
    # required leading "-" from URLs like t.me/c/1003049931114/...
    if normalized.startswith("100") and normalized.isdigit() and len(normalized) >= 13:
        return f"-{normalized}"

    return normalized
