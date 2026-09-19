# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody

"""Regression tests for audit fixes.

Covers three defects: `Media` lacking `is_live` (AttributeError on Telegram
file playback), the download cache treating yt-dlp `.part`/`.ytdl` artifacts
as finished files, and handlers KeyErroring on translation keys a locale does
not define.
"""

import os
import tempfile
import unittest
from pathlib import Path

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

from melody import lang  # noqa: E402
from melody.core.youtube import YouTube  # noqa: E402
from melody.helpers._dataclass import Media  # noqa: E402


class MediaIsLiveTest(unittest.TestCase):
    def test_defaults_false(self):
        self.assertFalse(Media(id="x").is_live)

    def test_explicit_value(self):
        self.assertTrue(Media(id="x", is_live=True).is_live)


class UsableFileTest(unittest.TestCase):
    def setUp(self):
        self.yt = YouTube()

    def test_rejects_incomplete_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("v.webm.part", "v.webm.part.ytdl", "v.webm.ytdl"):
                path = Path(tmp) / name
                path.write_bytes(b"data")
                self.assertFalse(self.yt._usable_file(path), name)

    def test_accepts_finished_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v.webm"
            path.write_bytes(b"data")
            self.assertTrue(self.yt._usable_file(path))
            self.assertFalse(self.yt._usable_file(Path(tmp) / "missing.webm"))

    def test_cached_download_ignores_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                Path("downloads").mkdir()
                (Path("downloads") / "vid.webm.part").write_bytes(b"partial")
                self.assertIsNone(self.yt.cached_download("vid"))
                (Path("downloads") / "vid.webm").write_bytes(b"complete")
                self.assertEqual(
                    self.yt.cached_download("vid"), "downloads/vid.webm"
                )
            finally:
                os.chdir(previous)

    def test_mtime_tolerates_missing_file(self):
        # Eviction can unlink between glob() and stat(); sorting must not raise.
        self.assertEqual(self.yt._mtime(Path("/nonexistent/file.webm")), 0.0)


class AdminCacheTTLTest(unittest.TestCase):
    """Stale admin cache must expire instead of locking in old permissions."""

    def setUp(self):
        from melody.core.mongo import MongoDB

        self.db = MongoDB.__new__(MongoDB)
        self.db.admin_list = {}
        self.db.admin_ts = {}
        self.reloads = []

        async def fake_reload(chat_id):
            self.reloads.append(chat_id)
            return [99]

        import melody.helpers._admins as admins_mod

        self._orig = admins_mod.reload_admins
        admins_mod.reload_admins = fake_reload

    def tearDown(self):
        import melody.helpers._admins as admins_mod

        admins_mod.reload_admins = self._orig

    def run_coro(self, coro):
        import asyncio

        return asyncio.new_event_loop().run_until_complete(coro)

    def test_reloads_after_ttl(self):
        self.assertEqual(self.run_coro(self.db.get_admins(1)), [99])
        # Fresh cache: no extra reload.
        self.assertEqual(self.run_coro(self.db.get_admins(1)), [99])
        self.assertEqual(len(self.reloads), 1)
        # Expire the TTL: reload happens again, values refresh.
        self.db.admin_ts[1] -= 1801
        self.assertEqual(self.run_coro(self.db.get_admins(1)), [99])
        self.assertEqual(len(self.reloads), 2)

    def test_reload_failure_keeps_fresh_timestamp(self):
        async def failing(chat_id):
            return None

        # Populate the cache first (setUp's fake_reload), then make reloads fail.
        self.assertEqual(self.run_coro(self.db.get_admins(1)), [99])
        import melody.helpers._admins as admins_mod

        orig = admins_mod.reload_admins
        admins_mod.reload_admins = failing
        try:
            ts = self.db.admin_ts[1]
            # Failure path must keep the cache AND its timestamp, else every
            # call refetches and stale entries never expire.
            self.assertGreater(ts, 0)
            self.assertEqual(self.run_coro(self.db.get_admins(1)), [99])
            self.assertEqual(self.db.admin_ts[1], ts)
        finally:
            admins_mod.reload_admins = orig


class LocaleFallbackTest(unittest.TestCase):
    def test_missing_keys_fall_back_to_english(self):
        english = lang.resolve("en")
        for code in ("hi", "de", "ru", "ar"):
            self.assertEqual(lang.resolve(code)["queue_empty"], english["queue_empty"])
            self.assertEqual(lang.resolve(code)["shuffled"], english["shuffled"])

    def test_unknown_code_falls_back_to_english(self):
        self.assertEqual(lang.resolve("zz"), lang.resolve("en"))

    def test_every_locale_has_every_english_key(self):
        english_keys = set(lang.resolve("en"))
        for code in lang.get_languages():
            self.assertTrue(english_keys <= set(lang.resolve(code)), code)


if __name__ == "__main__":
    unittest.main()