# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody

"""
Custom emoji for bot messages: name -> Telegram emoji document ID.

Get IDs from @DlEmojiIdBot. None keeps the plain Unicode emoji.
Custom emoji render for premium users only; others see the fallback.
"""

# document IDs from your emoji pack (None = plain emoji)
EMOJI_IDS: dict[str, int | None] = {
    "play": None,
    "pause": None,
    "resume": None,
    "skip": None,
    "stop": None,
    "download": None,
    "search": None,
    "queue": None,
    "seek": None,
    "replay": None,
    "music": None,
    "volume": None,
    "settings": None,
    "close": None,
    "back": None,
}


def emoji(key: str, fallback: str) -> str:
    """Wrap fallback in a tg-emoji tag, or return it unchanged if no ID."""
    doc_id = EMOJI_IDS.get(key)
    if not doc_id:
        return fallback
    return f'<tg-emoji emoji-id="{doc_id}">{fallback}</tg-emoji>'
