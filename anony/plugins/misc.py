# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time
import asyncio
from contextlib import suppress

from pyrogram import enums, errors, filters, types

from anony import anon, app, config, db, lang, logger, queue, tasks, userbot, yt
from anony.helpers import buttons


@app.on_message(filters.video_chat_started, group=19)
@app.on_message(filters.video_chat_ended, group=20)
async def _watcher_vc(_, m: types.Message):
    await anon.stop(m.chat.id)


async def auto_leave():
    while True:
        await asyncio.sleep(3600)
        for ub in userbot.clients:
            try:
                chats = [dialog.chat.id async for dialog in ub.get_dialogs()
                            if dialog.chat.type in [
                                enums.ChatType.GROUP, enums.ChatType.SUPERGROUP,
                            ]][-20:]
                for chat in chats:
                    if chat in [app.logger, -1001686672798, -1001549206010]:
                        continue
                    if chat in db.active_calls:
                        continue
                    await ub.leave_chat(chat)
                    await asyncio.sleep(12)
            except asyncio.CancelledError:
                raise
            except errors.FloodWait as ex:
                await asyncio.sleep(ex.value)
            except Exception as ex:
                logger.warning("auto_leave failed for assistant: %r", ex)
                continue


async def track_time():
    while True:
        await asyncio.sleep(1)
        for chat_id in list(db.active_calls):
            try:
                if not await db.playing(chat_id):
                    continue
                media = queue.get_current(chat_id)
                if not media:
                    continue
                media.time += 1
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                logger.warning("track_time failed for chat %s: %r", chat_id, ex)


async def update_timer(length=10, sleep=12):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            if not await db.playing(chat_id):
                continue
            try:
                media = queue.get_current(chat_id)
                if not media:
                    continue
                duration, message_id = media.duration_sec, media.message_id
                if not duration or not message_id or not media.time:
                    continue
                remove = False
                played = media.time
                remaining = max(duration - played, 0)
                pos = min(int((played / duration) * length), length - 1)
                timer = "—" * pos + "◉" + "—" * (length - pos - 1)

                if remaining <= 30:
                    next = queue.get_next(chat_id, check=True)
                    if next and not next.file_path:
                        next.file_path = await yt.download(next.id, video=next.video)

                if remaining < 10:
                    remove = True

                timer = f"{time.strftime('%M:%S', time.gmtime(played))} | {timer} | -{time.strftime('%M:%S', time.gmtime(remaining))}"

                if not timer and not remove:
                    continue

                await app.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=buttons.controls(
                        chat_id=chat_id, timer=timer, remove=remove
                    ),
                )
            except asyncio.CancelledError:
                raise
            except (errors.MessageNotModified, errors.MessageIdInvalid):
                pass
            except errors.FloodWait as ex:
                await asyncio.sleep(ex.value)
            except Exception as ex:
                logger.warning("update_timer failed for chat %s: %r", chat_id, ex)


async def vc_watcher(sleep=15):
    while True:
        await asyncio.sleep(sleep)
        for chat_id in list(db.active_calls):
            try:
                client = await db.get_assistant(chat_id)
                media = queue.get_current(chat_id)
                if not media:
                    continue
                # kurigram 2.2 removed get_participants; get_call_members
                # yields GroupCallMember objects for the active group call.
                participants = [m async for m in client.get_call_members(chat_id)]
                if len(participants) < 2 and media.time > 30:
                    _lang = await lang.get_lang(chat_id)
                    # The status-markup edit is cosmetic; if the now-playing
                    # message was deleted it raises MessageIdInvalid. Suppress
                    # it so the auto-stop below always runs.
                    sent = None
                    with suppress(errors.MessageNotModified, errors.MessageIdInvalid):
                        sent = await app.edit_message_reply_markup(
                            chat_id=chat_id,
                            message_id=media.message_id,
                            reply_markup=buttons.controls(
                                chat_id=chat_id, status=_lang["stopped"], remove=True
                            ),
                        )
                    await anon.stop(chat_id)
                    if sent:
                        with suppress(Exception):
                            await sent.reply_text(_lang["auto_left"])
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                logger.warning("vc_watcher failed for chat %s: %r", chat_id, ex)


if config.AUTO_END:
    tasks.append(asyncio.create_task(vc_watcher()))
if config.AUTO_LEAVE:
    tasks.append(asyncio.create_task(auto_leave()))
tasks.append(asyncio.create_task(track_time()))
tasks.append(asyncio.create_task(update_timer()))
