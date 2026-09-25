# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import asyncio
from html import escape

from pyrogram import filters, types

from melody import anon, app, config, db, lang, logger, queue, tg, yt
from melody.helpers import buttons, utils
from melody.helpers._play import checkUB


def playlist_to_queue(chat_id: int, tracks: list) -> tuple[str, int, int]:
    """Queue tracks within limits; return (list body, added, skipped)."""
    text = "<blockquote expandable>"
    added = 0
    skipped = 0
    for track in tracks:
        if track.duration_sec > config.DURATION_LIMIT:
            skipped += 1
            continue
        if queue.size(chat_id) >= config.QUEUE_LIMIT:
            skipped += 1
            continue
        pos = queue.add(chat_id, track)
        text += f"<b>{pos + 1}.</b> {escape(track.title)}\n"
        added += 1
    if len(text) > 1948:
        # Cut at the last line boundary so we never split an HTML tag/entity.
        text = text[:1948]
        text = text[: text.rfind("\n")] if "\n" in text else text
    text += "</blockquote>"
    return text, added, skipped


async def announce_playlist(m: types.Message, tracks: list) -> None:
    """Queue tracks and report the result."""
    body, added, skipped = playlist_to_queue(m.chat.id, tracks)
    text = m.lang["playlist_queued"].format(added) + body
    if skipped:
        text += "\n" + m.lang.get(
            "playlist_skipped",
            "<i>Skipped {0} track(s) (queue full or over the duration limit).</i>",
        ).format(skipped)
    await app.send_message(chat_id=m.chat.id, text=text)

@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
    shuffle: bool = False,
) -> None:
    sent = await m.reply_text(m.lang["play_searching"])
    file = None
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []
    # Early background download overlaps network time with queue checks.
    _dl_task: asyncio.Task | None = None

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    elif url:
        if "playlist" in url:
            await sent.edit_text(m.lang["playlist_fetch"])
            tracks = await yt.playlist(
                config.PLAYLIST_LIMIT, mention, url, video, shuffle
            )

            if not tracks:
                return await sent.edit_text(m.lang["playlist_error"])

            # Play the first within-limit track; don't let an over-long first
            # video abort the playlist.
            idx = next(
                (i for i, t in enumerate(tracks) if t.duration_sec <= config.DURATION_LIMIT),
                None,
            )
            if idx is None:
                return await sent.edit_text(
                    m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
                )

            file = tracks.pop(idx)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video)
        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT)
            )

    if not file:
        return await sent.edit_text(m.lang["play_usage"])

    # Duration limit doesn't apply to live (no duration).
    if file.duration_sec > config.DURATION_LIMIT and not getattr(file, "is_live", False):
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60)
        )

    # Download in background while local checks run; live resolves to a URL.
    if (
        not file.is_live
        and not file.file_path
        and not yt.cached_download(file.id, video=video)
    ):
        _dl_task = asyncio.create_task(yt.download(file.id, video=video))

    if await db.is_logger():
        try:
            await utils.play_log(
                m, sent.link, file.title, "🔴 LIVE" if file.is_live else file.duration
            )
        except Exception as ex:
            logger.warning("Play logging failed for %s: %r", m.chat.id, ex)

    file.user = mention
    async with anon.transition(m.chat.id):
        if force:
            queue.force_add(m.chat.id, file)
            position = 0
        else:
            if queue.size(m.chat.id) >= config.QUEUE_LIMIT:
                if _dl_task:
                    _dl_task.cancel()
                return await sent.edit_text(
                    m.lang["play_queue_full"].format(config.QUEUE_LIMIT)
                )
            position = queue.add(m.chat.id, file)

    if position != 0 or await db.get_call(m.chat.id):
        if _dl_task:
            _dl_task.cancel()
        await sent.edit_text(
            m.lang["play_queued"].format(
                position,
                escape(file.url, quote=True),
                escape(file.title),
                "🔴 LIVE" if file.is_live else file.duration,
                m.from_user.mention,
            ),
            reply_markup=buttons.play_queued(
                m.chat.id, file.id, m.lang["play_now"]
            ),
        )
        if tracks:
            await announce_playlist(m, tracks)
        return

    if not file.file_path:
        if file.is_live:
            await sent.edit_text(m.lang["play_downloading"])
            file.file_path = await yt.stream_url(file.id, video=video)
        else:
            file.file_path = yt.cached_download(file.id, video=video)
            if not file.file_path:
                if _dl_task:
                    await sent.edit_text(m.lang["play_downloading"])
                    file.file_path = await _dl_task
                    _dl_task = None
                else:
                    await sent.edit_text(m.lang["play_downloading"])
                    file.file_path = await yt.download(file.id, video=video)

    if _dl_task and not _dl_task.done():
        _dl_task.cancel()

    async with anon.transition(m.chat.id):
        if await db.get_call(m.chat.id):
            return await sent.edit_text(
                m.lang["play_queued"].format(
                    0,
                    escape(file.url, quote=True),
                    escape(file.title),
                    "🔴 LIVE" if file.is_live else file.duration,
                    m.from_user.mention,
                )
            )
        await anon.play_media(chat_id=m.chat.id, message=sent, media=file, _locked=True)
    if not tracks:
        return
    await announce_playlist(m, tracks)

