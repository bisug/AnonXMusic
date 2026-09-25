# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import re

from pyrogram import errors, filters, types

from melody import anon, app, db, lang, logger, queue, tg, yt
from melody.helpers import admin_check, buttons, can_manage_vc, utils
from melody.helpers import _rich


def _played_str(media):
    return utils.format_duration(min(media.time, media.duration_sec))


async def _edit_help_message(query: types.CallbackQuery, text: str, reply_markup):
    if query.message.caption is not None:
        return await query.edit_message_caption(caption=text, reply_markup=reply_markup)
    return await query.edit_message_text(text=text, reply_markup=reply_markup)


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    actions = {"status", "pause", "resume", "skip", "force", "replay", "stop"}
    if len(args) < 3 or args[1] not in actions:
        return await query.answer()
    if args[1] == "force" and len(args) != 4:
        return await query.answer()
    try:
        chat_id = int(args[2])
    except ValueError:
        return await query.answer()
    action = args[1]
    # Button must live in the target chat (blocks forwarded-message abuse).
    if not query.message or chat_id != query.message.chat.id:
        return await query.answer(query.lang["user_no_perms"], show_alert=True)
    qaction = len(args) == 4
    user = query.from_user.mention

    if not await db.get_call(chat_id):
        try:
            return await query.answer(query.lang["not_playing"], show_alert=True)
        except errors.QueryIdInvalid:
            try:
                await query.message.delete()
            except Exception:
                pass
            return

    if action == "status":
        media = queue.get_current(chat_id)
        if media and media.duration_sec and media.time:
            return await query.answer(f"{_played_str(media)} / {media.duration}")
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        await anon.pause(chat_id)
        if not qaction and getattr(query.message, "rich_message", None) is not None:
            await _rich.refresh_np(chat_id, playing=False, message=query.message)
            return await query.answer(query.lang["paused"])
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await anon.resume(chat_id)
        if not qaction and getattr(query.message, "rich_message", None) is not None:
            await _rich.refresh_np(chat_id, playing=True, message=query.message)
            return await query.answer(query.lang["playing"])
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True)
            )
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        current = queue.get_current(chat_id)
        m_id = current.message_id if current else 0
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except Exception:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            if getattr(media, "is_live", False):
                media.file_path = await yt.stream_url(media.id, video=media.video)
            else:
                media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        if not media:
            return
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action == "stop":
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["skip", "replay", "stop"]:
            await query.message.reply_text(reply, quote=False)
            await query.message.delete()
        else:
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                query.message.caption.html or query.message.text.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )
            await query.edit_message_text(
                f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
            )
    except (errors.MessageNotModified, errors.MessageIdInvalid):
        pass
    except Exception as ex:
        logger.warning(
            "controls '%s' update failed for chat %s: %r", action, chat_id, ex
        )


@app.on_callback_query(filters.regex("help") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    data = query.data.split()
    if len(data) == 1:
        await query.answer()
        return await _edit_help_message(
            query,
            text=query.lang["help_menu"],
            reply_markup=buttons.help_markup(query.lang),
        )

    if data[1] == "back":
        return await _edit_help_message(
            query,
            text=query.lang["help_menu"], reply_markup=buttons.help_markup(query.lang)
        )
    elif data[1] == "close":
        try:
            await query.message.delete()
            return await query.message.reply_to_message.delete()
        except Exception:
            return

    await _edit_help_message(
        query,
        text=query.lang[f"help_{data[1]}"],
        reply_markup=buttons.help_markup(query.lang, True),
    )


@app.on_callback_query(filters.regex("settings") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()
    if len(cmd) == 1:
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    chat_id = query.message.chat.id
    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)
    _no_thumb = await db.get_thumbnail_mode(chat_id)
    _autoplay = await db.get_autoplay(chat_id)

    if cmd[1] == "delete":
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif cmd[1] == "play":
        await db.set_play_mode(chat_id, _admin)
        _admin = not _admin
    elif cmd[1] == "thumbnail":
        _no_thumb = not _no_thumb
        await db.set_thumbnail_mode(chat_id, _no_thumb)
    elif cmd[1] == "autoplay":
        _autoplay = not _autoplay
        await db.set_autoplay(chat_id, _autoplay)
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            _admin,
            _delete,
            _language,
            chat_id,
            no_thumbnail=_no_thumb,
            autoplay=_autoplay,
        )
    )
