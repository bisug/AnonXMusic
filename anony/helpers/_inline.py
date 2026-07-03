# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import enums, types

from anony import app, config, lang
from anony.core.lang import format_lang_name


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton
        self.styles = {
            "default": enums.ButtonStyle.DEFAULT,
            "primary": enums.ButtonStyle.PRIMARY,
            "success": enums.ButtonStyle.SUCCESS,
            "danger": enums.ButtonStyle.DANGER,
            "status": enums.ButtonStyle.DEFAULT,
            "nav": enums.ButtonStyle.DEFAULT,
            "link": enums.ButtonStyle.DEFAULT,
            "menu": enums.ButtonStyle.PRIMARY,
            "media": enums.ButtonStyle.PRIMARY,
            "play": enums.ButtonStyle.SUCCESS,
            "setting": enums.ButtonStyle.PRIMARY,
            "enabled": enums.ButtonStyle.SUCCESS,
            "disabled": enums.ButtonStyle.DANGER,
        }

    def _button(self, text: str, category: str = "default", **kwargs):
        return self.ikb(
            text=text,
            style=self.styles.get(category, enums.ButtonStyle.DEFAULT),
            **kwargs,
        )

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [[self._button(text=text, category="danger", callback_data="cancel_dl")]]
        )

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            keyboard.append(
                [
                    self._button(
                        text=status,
                        category="status",
                        callback_data=f"controls status {chat_id}",
                    )
                ]
            )
        elif timer:
            keyboard.append(
                [
                    self._button(
                        text=timer,
                        category="status",
                        callback_data=f"controls status {chat_id}",
                    )
                ]
            )

        if not remove:
            keyboard.append(
                [
                    self._button(
                        text="▷",
                        category="play",
                        callback_data=f"controls resume {chat_id}",
                    ),
                    self._button(
                        text="II",
                        category="media",
                        callback_data=f"controls pause {chat_id}",
                    ),
                    self._button(
                        text="⥁",
                        category="media",
                        callback_data=f"controls replay {chat_id}",
                    ),
                    self._button(
                        text="‣‣I",
                        category="media",
                        callback_data=f"controls skip {chat_id}",
                    ),
                    self._button(
                        text="▢",
                        category="danger",
                        callback_data=f"controls stop {chat_id}",
                    ),
                ]
            )
        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        if back:
            rows = [
                [
                    self._button(
                        text=_lang["back"],
                        category="nav",
                        callback_data="help back",
                    ),
                    self._button(
                        text=_lang["close"],
                        category="danger",
                        callback_data="help close",
                    ),
                ]
            ]
        else:
            cbs = [
                "admins",
                "auth",
                "blist",
                "lang",
                "ping",
                "play",
                "queue",
                "stats",
                "sudo",
            ]
            buttons = [
                self._button(
                    text=_lang[f"help_{i}"],
                    category="menu",
                    callback_data=f"help {cb}",
                )
                for i, cb in enumerate(cbs)
            ]
            rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]

        return self.ikm(rows)

    def lang_markup(
        self, _lang: str, action: str = "lang_change"
    ) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()

        buttons = [
            self._button(
                text=f"{'✅ ' if code == _lang else ''}{format_lang_name(code)} ({code})",
                category="enabled" if code == _lang else "default",
                callback_data=f"{action} {code}",
            )
            for code in langs
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [[self._button(text=text, category="link", url=config.SUPPORT_CHAT)]]
        )

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self._button(
                        text=_text,
                        category="play",
                        callback_data=f"controls force {chat_id} {item_id}",
                    )
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        _category = "enabled" if playing else "disabled"
        return self.ikm(
            [
                [
                    self._button(
                        text=_text,
                        category=_category,
                        callback_data=f"controls {_action} {chat_id} q",
                    )
                ]
            ]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, cmd_delete: bool, language: str, chat_id: int,
        no_thumbnail: bool = False,
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self._button(
                        text=lang["play_mode"] + " ➜",
                        category="setting",
                        callback_data="settings",
                    ),
                    self._button(
                        text=admin_only,
                        category="enabled" if admin_only else "disabled",
                        callback_data="settings play",
                    ),
                ],
                [
                    self._button(
                        text=lang["cmd_delete"] + " ➜",
                        category="setting",
                        callback_data="settings",
                    ),
                    self._button(
                        text=cmd_delete,
                        category="enabled" if cmd_delete else "disabled",
                        callback_data="settings delete",
                    ),
                ],
                [
                    self._button(
                        text=lang["thumbnail"] + " ➜",
                        category="setting",
                        callback_data="settings",
                    ),
                    self._button(
                        text=lang["thumbnail_off"] if no_thumbnail else lang["thumbnail_on"],
                        category="disabled" if no_thumbnail else "enabled",
                        callback_data="settings thumbnail",
                    ),
                ],
                [
                    self._button(
                        text=lang["language"] + " ➜",
                        category="setting",
                        callback_data="settings",
                    ),
                    self._button(
                        text=format_lang_name(language),
                        category="menu",
                        callback_data="language",
                    ),
                ],
            ]
        )

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                self._button(
                    text=lang["add_me"],
                    category="play",
                    url=f"https://t.me/{app.username}?startgroup=true",
                )
            ],
            [
                self._button(
                    text=lang["help"], category="menu", callback_data="help"
                )
            ],
            [
                self._button(
                    text=lang["support"], category="link", url=config.SUPPORT_CHAT
                ),
                self._button(
                    text=lang["channel"], category="link", url=config.SUPPORT_CHANNEL
                ),
            ],
        ]
        if not private:
            rows += [
                [
                    self._button(
                        text=lang["language"],
                        category="menu",
                        callback_data="language",
                    )
                ]
            ]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self._button(text="❐", category="default", copy_text=link),
                    self._button(text="Youtube", category="link", url=link),
                ],
            ]
        )
