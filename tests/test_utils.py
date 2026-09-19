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

from melody.helpers import utils  # noqa: E402


class FormatETATest(unittest.TestCase):
    def test_under_minute(self):
        self.assertEqual(utils.format_eta(5), "5s")
        self.assertEqual(utils.format_eta(59), "59s")

    def test_minutes(self):
        self.assertEqual(utils.format_eta(60), "1:00 min")
        self.assertEqual(utils.format_eta(125), "2:05 min")

    def test_hours(self):
        self.assertEqual(utils.format_eta(3600), "1:00:00 h")
        self.assertEqual(utils.format_eta(7325), "2:02:05 h")


class FormatSizeTest(unittest.TestCase):
    def test_units(self):
        self.assertEqual(utils.format_size(512), "0.50 KB")
        self.assertEqual(utils.format_size(5 * 1024**2), "5.00 MB")
        self.assertEqual(utils.format_size(3 * 1024**3), "3.00 GB")


class ToSecondsTest(unittest.TestCase):
    def test_common_formats(self):
        self.assertEqual(utils.to_seconds("3:00"), 180)
        self.assertEqual(utils.to_seconds("1:02:05"), 3725)

    def test_live_and_garbage_return_zero(self):
        # "1:2:3:4" parses as 223384s — odd but pre-existing; not locked here.
        for value in ("LIVE", "", ":", None, "abc"):
            self.assertEqual(utils.to_seconds(value), 0)


if __name__ == "__main__":
    unittest.main()