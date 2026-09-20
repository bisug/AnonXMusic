# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


from pyrogram import filters, types

from melody import app, db, lang
from melody.helpers import can_manage_vc


@app.on_message(filters.command(["autoplay"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _autoplay(_, m: types.Message):
    chat_id = m.chat.id
    if len(m.command) < 2:
        state = await db.get_autoplay(chat_id)
        return await m.reply_text(m.lang["autoplay_status"].format("on" if state else "off"))

    arg = m.command[1].lower()
    if arg in ["on", "enable"]:
        await db.set_autoplay(chat_id, True)
        await m.reply_text(m.lang["autoplay_on"])
    elif arg in ["off", "disable"]:
        await db.set_autoplay(chat_id, False)
        await m.reply_text(m.lang["autoplay_off"])
    else:
        await m.reply_text(m.lang["autoplay_usage"])
