# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time

import pyrogram
from contextlib import suppress

from anony import config, logger


DEFAULT_SUPPORT_LINK = "https://t.me/SuMelodyVibes"
TELEGRAM_LINK_PREFIXES = ("https://t.me/", "http://t.me/", "t.me/", "telegram.me/")
# Re-resolve numeric-ID support links at most once an hour; URL values never
# need resolution at all.
_SUPPORT_TTL = 3600


class Bot(pyrogram.Client):
    def __init__(self):
        super().__init__(
            name="anony",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            parse_mode=pyrogram.enums.ParseMode.HTML,
            max_concurrent_transmissions=7,
            link_preview_options=pyrogram.types.LinkPreviewOptions(is_disabled=True),
        )
        self.owner = config.OWNER_ID
        self.logger = config.LOGGER_ID
        self.bl_users = pyrogram.filters.user()
        self.bl_chats = pyrogram.filters.chat()
        self.sudoers = pyrogram.filters.user(self.owner)

    @staticmethod
    def _support_chat_id(value: str) -> int | None:
        value = str(value or "").strip()
        if value.lstrip("-").isdigit():
            return int(value)
        return None

    @staticmethod
    def _support_url(value: str) -> str | None:
        value = str(value or "").strip()
        if not value:
            return None
        if value.startswith(("https://", "http://")):
            return value
        for prefix in TELEGRAM_LINK_PREFIXES:
            if value.startswith(prefix):
                return f"https://t.me/{value.removeprefix(prefix)}"
        if value.lstrip("-").isdigit():
            return None
        return f"https://t.me/{value.removeprefix('@')}"

    async def _resolve_support_link(self, attr: str) -> str:
        value = getattr(config, f"{attr}_RAW", getattr(config, attr, ""))
        if url := self._support_url(value):
            return url

        chat_id = self._support_chat_id(value)
        if chat_id is None:
            return DEFAULT_SUPPORT_LINK

        try:
            chat = await self.get_chat(chat_id)
            if chat.invite_link:
                return chat.invite_link
            return await self.export_chat_invite_link(chat_id)
        except Exception as ex:
            logger.warning(
                "Failed to generate %s invite link for %s: %s",
                attr,
                chat_id,
                ex,
            )
            return DEFAULT_SUPPORT_LINK

    async def resolve_support_links(self) -> None:
        config.SUPPORT_CHANNEL = await self._resolve_support_link("SUPPORT_CHANNEL")
        config.SUPPORT_CHAT = await self._resolve_support_link("SUPPORT_CHAT")
        self._support_resolved_at = time.monotonic()

    async def refresh_support_links(self) -> None:
        # Numeric-ID links cost 1-2 Telegram API calls per resolve; skip when
        # resolved recently (URL values resolve locally and are cheap anyway).
        resolved_at = getattr(self, "_support_resolved_at", 0)
        if time.monotonic() - resolved_at < _SUPPORT_TTL:
            return
        await self.resolve_support_links()

    async def boot(self):
        """
        Starts the bot and performs initial setup.

        Raises:
            SystemExit: If the bot fails to access the log group or is not an administrator in the logger group.
        """
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name
        self.username = self.me.username
        self.mention = self.me.mention

        try:
            await self.send_message(self.logger, "Bot Started")
            get = await self.get_chat_member(self.logger, self.id)
        except Exception as ex:
            raise SystemExit(f"Bot has failed to access the log group: {self.logger}\nReason: {ex}")

        if get.status != pyrogram.enums.ChatMemberStatus.ADMINISTRATOR:
            raise SystemExit("Please promote the bot as an admin in logger group.")

        await self.resolve_support_links()
        logger.info(f"Bot started as @{self.username}")

    async def exit(self):
        """
        Sends a shutdown notification to the logger group, then stops the bot.
        """
        if self.is_connected:
            with suppress(Exception):
                await self.send_message(self.logger, "Bot Stopped")
            await super().stop()
            logger.info("Bot stopped.")
