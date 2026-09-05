# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

"""
Custom emoji for bot messages.

Each entry maps a name to a Telegram emoji document ID. Get IDs by sending
your emoji to @DlEmojiIdBot. Leave a value as None to keep the plain
Unicode emoji from the locale files.

Note: custom emoji only render for premium users; others see the fallback.
"""

# document IDs from your emoji pack
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
    """Return `fallback` wrapped in a tg-emoji tag, or unchanged if no ID."""
    doc_id = EMOJI_IDS.get(key)
    if not doc_id:
        return fallback
    return f'<tg-emoji emoji-id="{doc_id}">{fallback}</tg-emoji>'
