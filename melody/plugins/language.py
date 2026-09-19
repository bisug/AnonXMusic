# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


from pyrogram import filters, types

from melody import app, config, db, lang
from melody.core.lang import format_lang_name
from melody.helpers import admin_check, buttons


async def _send_private_start(query: types.CallbackQuery, lang_dict: dict):
    if not await db.is_user(query.from_user.id):
        await db.add_user(query.from_user.id)

    await app.refresh_support_links()
    await query.message.reply_photo(
        photo=config.START_IMG,
        caption=lang_dict["start_pm"].format(query.from_user.first_name, app.name),
        reply_markup=buttons.start_key(lang_dict, True),
        quote=False,
    )


@app.on_message(filters.command(["lang", "language"]) & ~app.bl_users)
@lang.language()
async def _lang(_, m: types.Message):
    current = await db.get_lang(m.chat.id)
    keyboard = buttons.lang_markup(current)
    await m.reply_text(m.lang["lang_choose"], reply_markup=keyboard)


@app.on_callback_query(
    filters.regex(r"^(?:language|lang_(?:change|start|group))") & ~app.bl_users
)
@lang.language()
@admin_check
async def _lang_cb(_, query: types.CallbackQuery):
    data = query.data.split()
    if data[0] == "language":
        current = await db.get_lang(query.message.chat.id)
        keyboard = buttons.lang_markup(current)
        return await query.edit_message_text(
            query.lang["lang_choose"], reply_markup=keyboard
        )

    action, selected = data[0], data[1]
    current = await db.get_lang(query.message.chat.id)
    onboarding = action in {"lang_start", "lang_group"}
    selected_name = format_lang_name(selected)
    if current == selected and not onboarding:
        return await query.answer(
            query.lang["lang_same"].format(selected_name), show_alert=True
        )

    await db.set_lang(query.message.chat.id, selected)
    selected_lang = lang.languages[selected]
    await query.answer(
        selected_lang["lang_change"].format(selected_name), show_alert=True
    )
    await query.edit_message_text(selected_lang["lang_changed"].format(selected_name))

    if action == "lang_start":
        await _send_private_start(query, selected_lang)
