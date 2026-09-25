# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported, ConnectionError)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from melody import (app, config, db, lang, logger,
                   queue, thumb, userbot, yt)
from melody import is_shutting_down
from melody.helpers import Media, Track, buttons
from melody.helpers import _rich


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        # Prefetch downloads cancelled on stop.
        self._prefetch: dict[int, asyncio.Task] = {}
        self._chat_locks = defaultdict(asyncio.Lock)
        self._starting: set[int] = set()

    @asynccontextmanager
    async def transition(self, chat_id: int):
        """Serialize queue and call mutations for one chat."""
        async with self._chat_locks[chat_id]:
            yield

    @asynccontextmanager
    async def start_guard(self, chat_id: int):
        """Allow one new start while active chats may still enqueue."""
        if chat_id in db.active_calls:
            yield True
            return
        if chat_id in self._starting:
            yield False
            return
        self._starting.add(chat_id)
        try:
            yield True
        finally:
            self._starting.discard(chat_id)

    async def pause(self, chat_id: int) -> bool:
        async with self.transition(chat_id):
            return await self._pause(chat_id)

    async def _pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await client.pause(chat_id)
        await db.playing(chat_id, paused=True)
        return True

    async def resume(self, chat_id: int) -> bool:
        async with self.transition(chat_id):
            return await self._resume(chat_id)

    async def _resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await client.resume(chat_id)
        await db.playing(chat_id, paused=False)
        return True

    async def stop(self, chat_id: int) -> None:
        async with self.transition(chat_id):
            await self._stop(chat_id)

    async def _stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        prefetch = self._prefetch.pop(chat_id, None)
        if prefetch and not prefetch.done():
            prefetch.cancel()
        current = queue.get_current(chat_id)
        # No message deletion during shutdown (would hang).
        if current and current.message_id and not is_shutting_down():
            try:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=current.message_id,
                    revoke=True,
                )
            except Exception:
                pass

        await client.leave_call(chat_id, close=False)
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)

    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
        *,
        _locked: bool = False,
    ) -> None:
        if _locked:
            return await self._play_media(chat_id, message, media, seek_time)
        async with self.transition(chat_id):
            await self._play_media(chat_id, message, media, seek_time)

    async def _play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = None
        _thumb_task = None
        _no_thumb = await db.get_thumbnail_mode(chat_id)
        if config.THUMB_GEN and not seek_time and not _no_thumb:
            if isinstance(media, Track):
                _thumb_task = asyncio.create_task(thumb.generate(media))
            else:
                _thumb = config.DEFAULT_THUMB

        if (
            isinstance(media, Track)
            and (
                not media.file_path
                or not Path(media.file_path).is_file()
                or Path(media.file_path).stat().st_size == 0
            )
        ):
            media.file_path = await yt.download(media.id, video=media.video)

        if not media.file_path:
            if _thumb_task:
                _thumb_task.cancel()
                with suppress(asyncio.CancelledError):
                    await _thumb_task
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        # Live HLS is demuxed: "video|audio" pair for video mode, else one URL.
        is_live = getattr(media, "is_live", False)
        media_path = media.file_path
        audio_path = None
        if is_live and "|" in str(media.file_path):
            media_path, audio_path = media.file_path.split("|", 1)

        # Reconnect flags apply to URL inputs only (ignored for local files).
        # pytgcalls strips flags the installed ffmpeg doesn't advertise, so
        # newer flags (>= 6.1/7.1) degrade gracefully on older builds.
        ffmpeg_args = []
        if str(media_path).startswith(("http://", "https://")):
            ffmpeg_args.append(
                # Base (>= 5.0): reconnect, cover non-seekable, cap backoff.
                "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
                # Retry TCP/TLS and transient 5xx (>= 6.1).
                "-reconnect_on_network_error 1 "
                "-reconnect_on_http_error 429,500,502,503,504 "
                # Bound retries: 8 attempts, 30s backoff (>= 7.1).
                "-reconnect_max_retries 8 -reconnect_delay_total_max 30"
            )
        if seek_time > 1:
            ffmpeg_args.append(f"-ss {seek_time}")

        stream = types.MediaStream(
            media_path=media_path,
            audio_path=audio_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=" ".join(ffmpeg_args) if ffmpeg_args else None,
        )
        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                if _thumb_task:
                    _thumb = await _thumb_task
                media.time = 1
                await db.add_call(chat_id)
                # Prefetch next track; skipped for live (never ends).
                _next = queue.get_next(chat_id, check=True)
                if (
                    not is_live
                    and _next
                    and isinstance(_next, Track)
                    and not _next.is_live
                    and not _next.file_path
                ):
                    old = self._prefetch.pop(chat_id, None)
                    if old and not old.done():
                        old.cancel()
                    task = asyncio.create_task(
                        yt.download(_next.id, video=_next.video, prefetch=True)
                    )
                    self._prefetch[chat_id] = task
                    task.add_done_callback(
                        lambda t, c=chat_id: self._prefetch.pop(c, None)
                        if self._prefetch.get(c) is t
                        else None
                    )
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    "🔴 LIVE" if is_live else media.duration,
                    media.user,
                )
                keyboard = buttons.controls(chat_id)
                media.rich_ui = False
                if await _rich.edit_placeholder(
                    message, chat_id, media, _lang, thumb=_thumb
                ):
                    media.rich_ui = True
                    media.message_id = message.id
                else:
                    try:
                        if _thumb:
                            await message.edit_media(
                                media=InputMediaPhoto(
                                    media=_thumb,
                                    caption=text,
                                ),
                                reply_markup=keyboard,
                            )
                        else:
                            await message.edit_text(text, reply_markup=keyboard)
                    except Exception:
                        if _thumb:
                            sent = await app.send_photo(
                                chat_id=chat_id,
                                photo=_thumb,
                                caption=text,
                                reply_markup=keyboard,
                            )
                        else:
                            sent = await app.send_message(
                                chat_id=chat_id,
                                text=text,
                                reply_markup=keyboard,
                            )
                        media.message_id = sent.id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self._play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self._stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self._play_next(chat_id)
        except (ConnectionError, ConnectionNotFound, TelegramServerError):
            await self._stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self._stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])
        finally:
            if _thumb_task and not _thumb_task.done():
                _thumb_task.cancel()
                with suppress(asyncio.CancelledError):
                    await _thumb_task

    async def replay(self, chat_id: int) -> None:
        async with self.transition(chat_id):
            if not await db.get_call(chat_id):
                return

            media = queue.get_current(chat_id)
            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
            media.message_id = msg.id
            await self._play_media(chat_id, msg, media)

    async def play_next(self, chat_id: int) -> None:
        async with self.transition(chat_id):
            await self._play_next(chat_id)

    async def _play_next(self, chat_id: int) -> None:
        current = queue.get_current(chat_id)
        if current and current.message_id:
            try:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=current.message_id,
                    revoke=True,
                )
            except Exception:
                pass

        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            if not current:
                return await self._stop(chat_id)
            _lang = await lang.get_lang(chat_id)
            msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
            current.message_id = msg.id
            return await self._play_media(chat_id, msg, current)

        media = queue.get_next(chat_id)

        # Guard before any attribute access: empty queue ends playback,
        # unless autoplay can find a related track first.
        if not media:
            if current and await db.get_autoplay(chat_id):
                return await self._autoplay(chat_id, current)
            return await self._stop(chat_id)

        try:
            if media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except Exception:
            pass

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
        if not media.file_path:
            if getattr(media, "is_live", False):
                media.file_path = await yt.stream_url(media.id, video=media.video)
            else:
                media.file_path = await yt.download(media.id, video=media.video)
            if not media.file_path:
                await msg.edit_text(
                    _lang["error_no_file"].format(config.SUPPORT_CHAT)
                )
                return await self._play_next(chat_id)

        media.message_id = msg.id
        await self._play_media(chat_id, msg, media)

    async def _autoplay(self, chat_id: int, current) -> None:
        """Queue a related track and keep playing; stop when nothing found."""
        _lang = await lang.get_lang(chat_id)
        media = await yt.related(current, video=current.video)
        if not media:
            return await self._stop(chat_id)

        media.user = _lang["autoplay_label"]
        msg = await app.send_message(
            chat_id=chat_id,
            text=_lang["autoplay_next"].format(media.url, media.title),
        )
        media.file_path = await yt.download(media.id, video=media.video)
        if not media.file_path:
            await msg.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self._stop(chat_id)

        queue.add(chat_id, media)
        media.message_id = msg.id
        await self._play_media(chat_id, msg, media)

    async def ping(self) -> float:
        async def get_ping(client) -> float:
            return await asyncio.to_thread(lambda: client.ping)

        pings = await asyncio.gather(*(get_ping(client) for client in self.clients))
        return round(sum(pings) / len(pings), 2) if pings else 0.0


    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)


    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=300)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")


    async def exit(self) -> None:
        """Leave active calls and release PyTgCalls resources (shutdown path)."""
        clients = list(self.clients)
        if not clients:
            return

        # stop() skips message deletion during shutdown via is_shutting_down().
        for chat_id in list(db.active_calls):
            with suppress(Exception):
                await self.stop(chat_id)

        for client in clients:
            with suppress(Exception):
                for chat_id in list((await client.calls).keys()):
                    with suppress(Exception):
                        await client.leave_call(chat_id, close=False)

            executor = getattr(client, "executor", None)
            if executor:
                with suppress(Exception):
                    executor.shutdown(wait=False, cancel_futures=True)
            if hasattr(client, "_is_running"):
                client._is_running = False

        self.clients.clear()
        logger.info("PyTgCalls client(s) stopped.")
