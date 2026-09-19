# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import re
import shutil
import subprocess
from pathlib import Path

from melody import logger

# Minimum ffmpeg (base -reconnect* input flags need >= 5.0; newer flags are
# optional and auto-stripped by pytgcalls on older builds).
_FFMPEG_MIN = (5, 0)


def _assert_ffmpeg_version() -> None:
    """Fail closed on an old ffmpeg build; warn-and-continue on probe miss."""
    try:
        out = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except Exception as ex:
        logger.warning("Could not run 'ffmpeg -version': %s", ex)
        return

    m = re.search(r"ffmpeg version n?(\d+)\.(\d+)", out)
    if not m:
        first = out.splitlines()[0] if out else ""
        logger.warning("Could not parse ffmpeg version from: %s", first)
        return

    found = (int(m.group(1)), int(m.group(2)))
    if found < _FFMPEG_MIN:
        raise RuntimeError(
            f"FFmpeg >= {_FFMPEG_MIN[0]}.{_FFMPEG_MIN[1]} required, "
            f"found {found[0]}.{found[1]}."
        )
    logger.info("FFmpeg %d.%d detected.", *found)


def ensure_dirs():
    """Ensure runtime dirs exist; requires ffmpeg on PATH."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg must be installed and accessible in the system PATH.")

    _assert_ffmpeg_version()

    for dir in ["cache", "downloads"]:
        Path(dir).mkdir(parents=True, exist_ok=True)
    logger.info("Cache directories updated.")
