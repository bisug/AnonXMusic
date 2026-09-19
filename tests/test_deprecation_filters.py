"""Guards the startup warnings filter in melody/__init__.py.

Python 3.14 warns that ``asyncio.iscoroutinefunction`` is deprecated. uvloop
<= 0.22.1 calls it from its C layer, so the warning is reported once per
``loop.add_signal_handler()`` and blamed on our call site in melody/__main__.py.
The package silences exactly that message, and only while
``_uvloop_needs_deprecation_filter()`` says the installed uvloop is affected.
These tests fail if the filter is dropped while it is still needed, if the gate
drifts in either direction, if the pattern stops matching uvloop's real wording,
or if the filter is widened to the point of hiding unrelated deprecations.

Run with:

    uv run python -m unittest discover -s tests -v
"""

import os
import unittest
import warnings

# melody.config.check() runs at import time and raises SystemExit when these are
# unset; dummy values keep the module importable without a real deployment.
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

# Imported after the env setup above: melody.config.check() runs at import time.
from melody import _uvloop_needs_deprecation_filter

# Verbatim text CPython 3.14 and uvloop 0.22.1 emit.
UVLOOP_MESSAGE = (
    "'asyncio.iscoroutinefunction' is deprecated and slated for removal in "
    "Python 3.16; use inspect.iscoroutinefunction() instead"
)
# A different deprecation that must stay visible.
UNRELATED_MESSAGE = "'asyncio.get_event_loop' is deprecated"


def _our_ignore_filters() -> list:
    """Ignore-filters for DeprecationWarning that target iscoroutinefunction."""
    return [
        entry
        for entry in warnings.filters
        if entry[0] == "ignore"
        and entry[2] is DeprecationWarning
        and entry[1] is not None
        and "iscoroutinefunction" in entry[1].pattern
    ]


class UvloopVersionGateTest(unittest.TestCase):
    def test_affected_versions_are_flagged(self):
        for affected in ("0.22.1", "0.22.0", "0.21.5", "0.20.0"):
            self.assertTrue(
                _uvloop_needs_deprecation_filter(affected),
                f"uvloop {affected} still needs the filter",
            )

    def test_fixed_versions_clear_the_gate(self):
        for fixed in ("0.22.2", "0.23.0", "0.30.0", "1.0.0"):
            self.assertFalse(
                _uvloop_needs_deprecation_filter(fixed),
                f"uvloop {fixed} no longer needs the filter",
            )

    def test_unparseable_versions_fail_safe(self):
        """An unknown version must not hide a deprecation we cannot rule out."""
        for junk in ("", "unknown", "v0.22.1.dev0+junk"):
            self.assertFalse(_uvloop_needs_deprecation_filter(junk))


class DeprecationFilterTest(unittest.TestCase):
    def test_filter_state_matches_the_gate(self):
        """Filter installed iff the installed uvloop needs it — no stale debt."""
        ours = _our_ignore_filters()
        if _uvloop_needs_deprecation_filter():
            self.assertTrue(ours, "melody dropped its uvloop DeprecationWarning filter")
            self.assertTrue(
                any(entry[1].match(UVLOOP_MESSAGE) for entry in ours),
                "the filter no longer matches uvloop's actual warning text",
            )
        else:
            self.assertFalse(
                ours,
                "uvloop is fixed, so the filter should have retired itself",
            )

    def test_filter_does_not_hide_unrelated_warnings(self):
        ours = _our_ignore_filters()
        self.assertFalse(
            any(entry[1].match(UNRELATED_MESSAGE) for entry in ours),
            "the filter is too broad and would hide unrelated deprecations",
        )


if __name__ == "__main__":
    unittest.main()
