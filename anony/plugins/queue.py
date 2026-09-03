# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import filters, types

from anony import anon, app, config, db, lang, queue, thumb
from anony.helpers import Track, buttons, can_manage_vc


@app.on_message(filters.command(["shuffle"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _shuffle(_, m: types.Message):
    """Shuffle the upcoming queue (current track keeps playing)."""
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    items = queue.get_queue(m.chat.id)
    if len(items) < 3:
        return await m.reply_text(m.lang["shuffle_need_more"])

    import random
    upcoming = items[1:]
    random.shuffle(upcoming)
    queue.set_queue(m.chat.id, [items[0], *upcoming])
    await m.reply_text(m.lang["shuffled"].format(len(upcoming)))


@app.on_message(filters.command(["clear"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _clear(_, m: types.Message):
    """Clear the upcoming queue; the current track keeps playing."""
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    items = queue.get_queue(m.chat.id)
    if len(items) < 2:
        return await m.reply_text(m.lang["queue_empty"])

    queue.set_queue(m.chat.id, items[:1])
    await m.reply_text(m.lang["queue_cleared"].format(len(items) - 1))


@app.on_message(filters.command(["queue", "playing"]) & filters.group & ~app.bl_users)
@lang.language()
async def _queue_func(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    _reply = await m.reply_text(m.lang["queue_fetching"])
    _queue = queue.get_queue(m.chat.id)
    if not _queue:
        return await _reply.edit_text(m.lang["not_playing"])
    _media = _queue[0]
    _thumb = (
        await thumb.generate(_media)
        if isinstance(_media, Track)
        else config.DEFAULT_THUMB
    ) if config.THUMB_GEN else None
    _text = m.lang["queue_curr"].format(
        _media.url,
        _media.title[:50],
        _media.duration,
        _media.user,
    )
    _queue.pop(0)

    if _queue:
        _text += "<blockquote expandable>"
        shown = 0
        for i, media in enumerate(_queue, start=1):
            if i == 15:
                break
            _text += m.lang["queue_item"].format(
                i, media.title, media.duration
            )
            shown += 1
        _text += "</blockquote>"
        if len(_queue) > shown:
            _text += "\n<i>" + m.lang.get(
                "queue_more", "+{0} more…"
            ).format(len(_queue) - shown) + "</i>"

    _playing = await db.playing(m.chat.id)
    _buttons = buttons.queue_markup(
            m.chat.id,
            m.lang["playing"] if _playing else m.lang["paused"],
            _playing,
        )
    if _thumb:
        await _reply.edit_media(
            media=types.InputMediaPhoto(
                media=_thumb,
                caption=_text,
            ),
            reply_markup=_buttons,
        )
    else:
        await _reply.edit_text(
            text=_text,
            reply_markup=_buttons,
        )
