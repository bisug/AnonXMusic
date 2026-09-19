# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody

import os
import unittest

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

from melody.core.bot import Bot, TELEGRAM_LINK_PREFIXES  # noqa: E402
from melody.core.youtube import YouTube  # noqa: E402


class SupportURLTest(unittest.TestCase):
    def test_full_urls_pass_through(self):
        self.assertEqual(Bot._support_url("https://t.me/mychan"), "https://t.me/mychan")

    def test_bare_and_at_handles(self):
        self.assertEqual(Bot._support_url("@foo"), "https://t.me/foo")
        self.assertEqual(Bot._support_url("foo"), "https://t.me/foo")

    def test_prefixed_bare_handles_get_normalized(self):
        for prefix in TELEGRAM_LINK_PREFIXES:
            # http:// prefix is passed through as-is, not upgraded to https.
            self.assertEqual(
                Bot._support_url(f"{prefix}foo"), f"https://t.me/foo".replace("https", "http") if prefix.startswith("http:") else "https://t.me/foo"
            )

    def test_numeric_id_is_not_a_url(self):
        # IDs must fall through to _support_chat_id, never render as links.
        self.assertEqual(Bot._support_url("-1001234567890"), None)

    def test_empty_is_none(self):
        self.assertEqual(Bot._support_url(""), None)
        self.assertEqual(Bot._support_url(None), None)

    def test_chat_id_parsing(self):
        self.assertEqual(Bot._support_chat_id("-1001234567890"), -1001234567890)
        self.assertEqual(Bot._support_chat_id("123456"), 123456)
        self.assertEqual(Bot._support_chat_id("https://t.me/foo"), None)


class YouTubeRegexTest(unittest.TestCase):
    def setUp(self):
        self.yt = YouTube()

    def test_valid_urls(self):
        for url in (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/playlist?list=PL1234567890",
            "www.youtube.com/watch?v=dQw4w9WgXcQ",
        ):
            self.assertTrue(self.yt.valid(url), url)

    def test_invalid_urls(self):
        for url in (
            "https://vimeo.com/12345",
            "https://github.com/foo/bar",
            # Non-video YouTube paths must not match the video regex…
            "https://www.youtube.com/channel/UCxyz",
            "https://www.youtube.com/@handle",
        ):
            self.assertFalse(self.yt.valid(url), url)
        # …but short/odd video IDs do match by design (regex allows 8–11 chars,
        # kept loose to not reject legacy uploads) — locked as valid.
        self.assertTrue(self.yt.valid("https://youtube.com/watch?v=abcdefghij"))

    def test_invalid_flags_non_video_youtube_paths(self):
        for url in (
            "https://www.youtube.com/channel/UCxyz",
            "https://www.youtube.com/@handle",
            "https://www.youtube.com/feed/subscriptions",
        ):
            self.assertTrue(self.yt.invalid(url), url)

    def test_valid_video_is_not_invalid(self):
        self.assertFalse(self.yt.invalid("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))


if __name__ == "__main__":
    unittest.main()