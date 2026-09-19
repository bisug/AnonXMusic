# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import asyncio
import json
import shutil
import time
from contextlib import suppress

import psutil
from pyrogram import filters, types

from melody import anon, app, boot, config, db, lang, logger
from melody.helpers import buttons

# Ookla's official Speedtest CLI — a Go binary, not the old speedtest-cli package.
# Its JSON is written to stdout, progress to stderr.
_OOKLA_CMD = (
    "speedtest",
    "--accept-license",
    "--accept-gdpr",
    "--format=json",
    "--progress=no",
)
# A full test takes 10-30s; cap it so a hung server can't stall /ping forever.
_OOKLA_TIMEOUT = 90


def _bandwidth_mbps(bytes_per_second: float) -> str:
    """Ookla reports bandwidth in bytes/second; render it as Mbps."""
    return f"{bytes_per_second * 8 / 1_000_000:.2f} Mbps"


async def _run_speedtest() -> str:
    if not shutil.which(_OOKLA_CMD[0]):
        logger.debug("Ookla Speedtest CLI not found in PATH; skipping speed test.")
        return "N/A"

    proc = await asyncio.create_subprocess_exec(
        *_OOKLA_CMD,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), _OOKLA_TIMEOUT
        )
    except TimeoutError:
        logger.warning("Speedtest timed out after %ss.", _OOKLA_TIMEOUT)
        return "N/A"
    except Exception as ex:
        logger.warning("Speedtest failed: %r", ex)
        return "N/A"
    finally:
        # Never leave the child running, whichever way we exit.
        if proc.returncode is None:
            with suppress(ProcessLookupError):
                proc.kill()
            with suppress(Exception):
                await proc.wait()  # reap it, so no zombie or GC warning

    if proc.returncode != 0:
        logger.warning(
            "Speedtest exited with %s: %s",
            proc.returncode,
            stderr.decode(errors="replace").strip(),
        )
        return "N/A"

    try:
        result = json.loads(stdout)
        return (
            f"DL: {_bandwidth_mbps(result['download']['bandwidth'])} | "
            f"UL: {_bandwidth_mbps(result['upload']['bandwidth'])} | "
            f"Ping: {result['ping']['latency']:.2f}ms"
        )
    except (ValueError, KeyError, TypeError) as ex:
        logger.warning("Unexpected speedtest result: %r", ex)
        return "N/A"


async def _db_latency() -> str:
    start = time.perf_counter()
    try:
        await db.mongo.admin.command("ping")
    except Exception as ex:
        logger.warning("DB latency ping failed: %r", ex)
        return "N/A"
    return f"{round((time.perf_counter() - start) * 1000, 2)}ms"


@app.on_message(filters.command(["alive", "ping"]) & ~app.bl_users)
@lang.language()
async def _ping(_, m: types.Message):
    start = time.perf_counter()
    sent = await m.reply_text(m.lang["pinging"])
    # Speedtest takes 10-30s — run it only for /ping speed, not every ping.
    full = any(tok in ("-s", "speed", "full") for tok in m.command[1:])
    network_speed_task = asyncio.create_task(_run_speedtest()) if full else None
    db_latency_task = asyncio.create_task(_db_latency())
    calls_latency_task = asyncio.create_task(anon.ping())

    def get_time(seconds: int) -> str:
        """Render seconds as "1days, 2:3:4" (days omitted at zero)."""
        parts = [
            f"{value}{unit}"
            for value, unit in zip(
                [
                    seconds % 60,
                    (seconds // 60) % 60,
                    (seconds // 3600) % 24,
                    seconds // 86400,
                ],
                ["s", "m", "h", "days"],
            )
        ]
        return (f"{parts[-1]}, " if parts[-1][:-4] != "0" else "") + ":".join(
            reversed(parts[:-1])
        )

    uptime = get_time(int(time.time() - boot))
    latency = round((time.perf_counter() - start) * 1000, 2)
    network_speed, db_latency, calls_latency = await asyncio.gather(
        network_speed_task or asyncio.sleep(0, result=None),
        db_latency_task,
        calls_latency_task,
    )
    caption = m.lang["ping_pong"].format(
        latency,
        uptime,
        psutil.cpu_percent(interval=0),
        psutil.virtual_memory().percent,
        psutil.disk_usage("/").percent,
        calls_latency,
    )
    caption += f"\n<b>DB Latency:</b> <code>{db_latency}</code>"
    if network_speed:
        caption += f"\n<b>Speedtest:</b> <code>{network_speed}</code>"
    await sent.edit_media(
        media=types.InputMediaPhoto(
            media=config.PING_IMG,
            caption=caption,
        ),
        reply_markup=buttons.ping_markup(m.lang["support"]),
    )
