# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody

"""Concurrency guard for Telegram file downloads.

`Telegram.download` registers the file id in `self.active` while a download is
in flight. A second call must not release that id: doing so let a third call
start a duplicate download writing to the same `<path>.temp`, corrupting it.
"""

import asyncio
import os
import unittest
import uuid

from pyrogram import StopPropagation

# melody.config.check() runs at import time and raises SystemExit when these are
# unset; dummy values keep the package importable without a real deployment.
for _var, _default in (
    ("API_ID", "1"),
    ("API_HASH", "x"),
    ("BOT_TOKEN", "x"),
    ("MONGO_URL", "mongodb://localhost:27017"),
    ("LOGGER_ID", "1"),
    ("OWNER_ID", "1"),
    ("SESSION", "x"),
):
    os.environ.setdefault(_var, _default)

from melody.core.telegram import Telegram  # noqa: E402


class _FakeMedia:
    def __init__(self):
        self.file_unique_id = f"test-{uuid.uuid4().hex}"
        self.file_name = "clip.mp3"
        self.file_size = 1024
        self.title = "clip"
        self.duration = 0
        self.mime_type = "audio/mpeg"


class _FakeMessage:
    def __init__(self, media, started, release):
        self.audio = media
        self.voice = self.video = self.document = None
        self.link = "https://t.me/c/1/2"
        self._started = started
        self._release = release
        self.calls = 0

    async def download(self, file_name=None, progress=None):
        self.calls += 1
        self._started.set()
        await self._release.wait()
        return file_name


class _FakeSent:
    def __init__(self, message_id):
        self.id = message_id
        self.lang = {"dl_active": "already downloading", "dl_complete": "done {0}"}

    async def edit_text(self, *args, **kwargs):
        return self

    async def stop_propagation(self):
        raise StopPropagation


class DownloadGuardTest(unittest.TestCase):
    def test_concurrent_same_file_triggers_one_download(self):
        async def scenario():
            tg = Telegram()
            media = _FakeMedia()
            started, release = asyncio.Event(), asyncio.Event()
            msg = _FakeMessage(media, started, release)

            first = asyncio.create_task(tg.download(msg, _FakeSent(1)))
            await started.wait()

            # A second call for the same file while the first is in flight must not
            # clear the guard registered by the first.
            with self.assertRaises(StopPropagation):
                await tg.download(msg, _FakeSent(2))
            self.assertIn(media.file_unique_id, tg.active)

            # A third call must therefore still see the guard and skip.
            with self.assertRaises(StopPropagation):
                await tg.download(msg, _FakeSent(3))

            release.set()
            await first
            return msg.calls, tg.active, first.exception()

        calls, active, first_error = asyncio.run(scenario())
        self.assertEqual(calls, 1)
        self.assertEqual(active, set())
        self.assertIsNone(first_error)


if __name__ == "__main__":
    unittest.main()