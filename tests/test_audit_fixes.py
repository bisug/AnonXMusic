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