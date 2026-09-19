"""Offline tests for the /ping speed-test helpers.

No network and no Ookla binary are needed: PATH lookup and the subprocess are
faked, so this locks in the parsing and failure contract of
melody/plugins/ping.py. Run with:

    uv run python -m unittest discover -s tests -v
"""

import asyncio
import json
import os
import unittest
from unittest import mock

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

from melody.plugins import ping

# Shape of `speedtest --format=json`; bandwidth is bytes/second.
OOKLA_SAMPLE = {
    "type": "result",
    "ping": {"jitter": 1.2, "latency": 12.34},
    "download": {"bandwidth": 12_500_000},
    "upload": {"bandwidth": 2_500_000},
}


class FakeProc:
    """Stands in for asyncio.subprocess.Process.

    ``returncode`` stays None until the process is observed to exit, matching
    the real class — the production code relies on that to decide whether a
    child needs killing.
    """

    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout, self._stderr = stdout, stderr
        self._exit_code = returncode
        self.returncode: int | None = None
        self.killed = False
        self.reaped = False

    async def communicate(self):
        self.returncode = self._exit_code
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True

    async def wait(self):
        self.reaped = True
        self.returncode = self._exit_code
        return self.returncode


def run_speedtest(proc: FakeProc, which: str | None = "/usr/bin/speedtest") -> str:
    spawner = mock.AsyncMock(return_value=proc)
    with (
        mock.patch.object(ping.shutil, "which", return_value=which),
        mock.patch("asyncio.create_subprocess_exec", new=spawner),
    ):
        return asyncio.run(ping._run_speedtest())


class BandwidthUnitTest(unittest.TestCase):
    def test_bytes_per_second_rendered_as_mbps(self):
        self.assertEqual(ping._bandwidth_mbps(12_500_000), "100.00 Mbps")

    def test_zero(self):
        self.assertEqual(ping._bandwidth_mbps(0), "0.00 Mbps")


class CommandTest(unittest.TestCase):
    def test_command_stays_machine_readable(self):
        # The parser reads JSON from stdout; human-readable output would break it.
        self.assertIn("--format=json", ping._OOKLA_CMD)
        self.assertIn("--progress=no", ping._OOKLA_CMD)
        self.assertIn("--accept-license", ping._OOKLA_CMD)
        self.assertIn("--accept-gdpr", ping._OOKLA_CMD)


class RunSpeedtestTest(unittest.TestCase):
    def test_missing_binary_returns_na_without_spawning(self):
        with (
            mock.patch.object(ping.shutil, "which", return_value=None),
            mock.patch("asyncio.create_subprocess_exec", new=mock.AsyncMock()) as spawn,
        ):
            self.assertEqual(asyncio.run(ping._run_speedtest()), "N/A")
        spawn.assert_not_called()

    def test_parses_ookla_json(self):
        proc = FakeProc(stdout=json.dumps(OOKLA_SAMPLE).encode())
        expected = "DL: 100.00 Mbps | UL: 20.00 Mbps | Ping: 12.34ms"
        self.assertEqual(run_speedtest(proc), expected)
        self.assertFalse(proc.killed)

    def test_nonzero_exit_returns_na(self):
        proc = FakeProc(stderr=b"no servers", returncode=1)
        self.assertEqual(run_speedtest(proc), "N/A")

    def test_missing_fields_returns_na(self):
        proc = FakeProc(stdout=json.dumps({"download": {"bandwidth": 1000}}).encode())
        self.assertEqual(run_speedtest(proc), "N/A")

    def test_non_json_returns_na(self):
        self.assertEqual(run_speedtest(FakeProc(stdout=b"<html>nope</html>")), "N/A")

    def test_timeout_kills_and_reaps_child(self):
        def _expire(coro, timeout):
            coro.close()  # the fake's coroutine is discarded, not awaited
            raise TimeoutError

        proc = FakeProc(stdout=json.dumps(OOKLA_SAMPLE).encode())
        spawner = mock.AsyncMock(return_value=proc)
        with (
            mock.patch.object(ping.shutil, "which", return_value="/usr/bin/speedtest"),
            mock.patch("asyncio.create_subprocess_exec", new=spawner),
            mock.patch("asyncio.wait_for", side_effect=_expire),
        ):
            self.assertEqual(asyncio.run(ping._run_speedtest()), "N/A")
        self.assertTrue(proc.killed)
        self.assertTrue(proc.reaped, "killed child must be reaped")


if __name__ == "__main__":
    unittest.main()
