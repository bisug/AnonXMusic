# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import json
from functools import wraps
from pathlib import Path

from pyrogram import errors

from melody import config, db, logger

lang_codes = {
    "ar": "العربية",
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "hi": "हिन्दी",
    "ja": "日本語",
    "my": "မြန်မာဘာသာ",
    "pa": "ਪੰਜਾਬੀ",
    "pt": "Português",
    "ru": "Русский",
    "tr": "Türkçe",
    "zh": "中文"
}

lang_flags = {
    "ar": "🇸🇦",
    "de": "🇩🇪",
    "en": "🇬🇧",
    "es": "🇪🇸",
    "fr": "🇫🇷",
    "hi": "🇮🇳",
    "ja": "🇯🇵",
    "my": "🇲🇲",
    "pa": "🇮🇳",
    "pt": "🇵🇹",
    "ru": "🇷🇺",
    "tr": "🇹🇷",
    "zh": "🇨🇳",
}


def format_lang_name(code: str) -> str:
    flag = lang_flags.get(code, "")
    name = lang_codes.get(code, code)
    return f"{flag} {name}".strip()


class Language:
    """Multilingual support backed by JSON locale files."""

    def __init__(self):
        self.lang_codes = lang_codes
        self.lang_dir = Path("melody/locales")
        self.languages = self.load_files()

    def load_files(self):
        languages = {}
        lang_files = {file.stem: file for file in self.lang_dir.glob("*.json")}
        for lang_code, lang_file in lang_files.items():
            with open(lang_file, encoding="utf-8") as file:
                languages[lang_code] = json.load(file)
        # Merge English underneath every locale so a missing translation key
        # can never KeyError a handler (queue/shuffle keys were absent from
        # most locales). Per-locale values still win.
        if "en" in languages:
            base = languages["en"]
            languages = {code: {**base, **data} for code, data in languages.items()}
        logger.info(f"Loaded languages: {', '.join(languages.keys())}")
        return languages

    def resolve(self, lang_code: str) -> dict:
        """Locale dict for a code, falling back to config/en for unknown codes."""
        return (
            self.languages.get(lang_code)
            or self.languages.get(config.LANG_CODE)
            or self.languages.get("en")
            or next(iter(self.languages.values()))
        )

    async def get_lang(self, chat_id: int) -> dict:
        lang_code = await db.get_lang(chat_id)
        return self.resolve(lang_code)

    def get_languages(self) -> dict:
        # Reuse the locales loaded at startup instead of re-globbing the dir.
        return {code: self.lang_codes.get(code, code) for code in sorted(self.languages)}

    def language(self):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                fallen = next(
                    (
                        arg
                        for arg in args
                        if hasattr(arg, "chat") or hasattr(arg, "message")
                    ),
                    None,
                )

                if not fallen.from_user:
                    return

                if hasattr(fallen, "chat"):
                    chat = fallen.chat
                elif hasattr(fallen, "message"):
                    chat = fallen.message.chat

                if not chat: return

                if chat.id in db.blacklisted:
                    logger.info(f"Chat {chat.id} is blacklisted, leaving...")
                    return await chat.leave()

                lang_code = await db.get_lang(chat.id)
                lang_dict = self.resolve(lang_code)

                fallen.lang = lang_dict
                try:
                    return await func(*args, **kwargs)
                except (errors.ChannelPrivate, errors.MessageIdInvalid, errors.MessageNotModified):
                    return
                except (
                    errors.Forbidden,
                    errors.ChatWriteForbidden,
                ):
                    return

            return wrapper

        return decorator
