from __future__ import annotations

from bots import telegram_bot


def test_send_telegram_uses_channel_id(monkeypatch):
    captured = {}

    class FakeBot:
        def __init__(self, token):
            captured["token"] = token

        async def send_message(self, chat_id, text):
            captured["chat_id"] = chat_id
            captured["text"] = text

    monkeypatch.setattr(telegram_bot, "Bot", FakeBot)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "-1003049931114")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1003049931114")

    result = telegram_bot.send_telegram("hello")

    assert result["sent"] is True
    assert captured == {"token": "token", "chat_id": "-1003049931114", "text": "hello"}


def test_send_telegram_normalizes_channel_style_chat_id(monkeypatch):
    captured = {}

    class FakeBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text):
            captured["chat_id"] = chat_id

    monkeypatch.setattr(telegram_bot, "Bot", FakeBot)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.delenv("TELEGRAM_CHANNEL_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1003049931114")

    result = telegram_bot.send_telegram("hello")

    assert result["sent"] is True
    assert captured["chat_id"] == "-1003049931114"


def test_truncate_caption_preserves_telegram_limit():
    message = "word " * 300

    caption = telegram_bot._truncate_caption(message)

    assert len(caption) <= telegram_bot.TELEGRAM_CAPTION_LIMIT
    assert caption.endswith("...")
