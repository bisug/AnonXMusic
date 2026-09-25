# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


from html import escape

from pyrogram import filters, types

from melody import anon, app, config, db, lang, logger, queue, tg, yt
from melody.helpers import buttons, can_manage_vc
from melody.helpers._play import join_assistant


@app.on_message(filters.command(["channelplay"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _channel_play(_, m: types.Message):
    chat_id = m.chat.id
    arg = m.command[1].lower() if len(m.command) > 1 else ""

    if arg in ["off", "disable"]:
        await db.set_channel_play(chat_id, None)
        return await m.reply_text(m.lang["channel_play_off"])
    if arg not in ["on", "enable"]:
        return await m.reply_text(m.lang["channel_play_usage"])

    try:
        linked = (await app.get_chat(chat_id)).linked_chat
    except Exception as ex:
        logger.warning("channelplay link lookup failed for %s: %r", chat_id, ex)
        linked = None
    if not linked:
        return await m.reply_text(m.lang["channel_no_linked"])

    await db.set_channel_play(chat_id, linked.id)
    await m.reply_text(m.lang["channel_play_on"].format(linked.title))


def _linked_channel_post(_, __, m: types.Message) -> bool:
    # Auto-forwarded channel posts have no from_user in groups; this also
    # keeps bot messages and user commands out of the watcher.
    return m.from_user is None and m.sender_chat is not None


@app.on_message(
    filters.group & filters.create(_linked_channel_post) & ~app.bl_users, group=6
)
async def _channel_watch(_, m: types.Message):
    chat_id = m.chat.id
    if m.sender_chat.id != await db.get_channel_play(chat_id):
        return
    if not (m.audio or m.voice or m.video or m.document):
        return

    _lang = await lang.get_lang(chat_id)
    async with anon.transition(chat_id):
        if queue.size(chat_id) >= config.QUEUE_LIMIT:
            return

    sent = await m.reply_text(_lang["play_searching"])
    sent.lang = _lang
    file = await tg.download(m, sent)
    if not file:
        return

    file.user = m.sender_chat.title or "Channel"

    if await db.get_call(chat_id):
        async with anon.transition(chat_id):
            if queue.size(chat_id) >= config.QUEUE_LIMIT:
                return await sent.delete()
            position = queue.add(chat_id, file)
        return await sent.edit_text(
            _lang["play_queued"].format(
                position,
                escape(file.url or "", quote=True),
                escape(file.title),
                "🔴 LIVE" if file.is_live else file.duration,
                escape(file.user or ""),
            ),
            reply_markup=buttons.play_queued(chat_id, file.id, _lang["play_now"]),
        )

    if not await join_assistant(m, _lang):
        return await sent.delete()

    if not file.file_path:
        if file.is_live:
            file.file_path = await yt.stream_url(file.id, video=file.video)
        else:
            file.file_path = await yt.download(file.id, video=file.video)

    if await db.get_call(chat_id):
        async with anon.transition(chat_id):
            if queue.size(chat_id) >= config.QUEUE_LIMIT:
                return await sent.delete()
            position = queue.add(chat_id, file)
        return await sent.edit_text(
            _lang["play_queued"].format(
                position,
                escape(file.url or "", quote=True),
                escape(file.title),
                "🔴 LIVE" if file.is_live else file.duration,
                escape(file.user or ""),
            ),
            reply_markup=buttons.play_queued(chat_id, file.id, _lang["play_now"]),
        )

    async with anon.start_guard(chat_id) as allowed:
        if not allowed:
            return await sent.delete()
        async with anon.transition(chat_id):
            if queue.size(chat_id) >= config.QUEUE_LIMIT:
                return await sent.delete()
            queue.add(chat_id, file)
            await anon.play_media(chat_id, sent, file, _locked=True)
