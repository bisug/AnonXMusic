# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
import time
import psutil
import speedtest

from pyrogram import filters, types
from anony import app, anon, boot, config, db, lang, logger
from anony.helpers import buttons


def _format_mbps(bits_per_second: float) -> str:
    return f"{bits_per_second / 1_000_000:.2f} Mbps"


def _run_speedtest() -> str:
    test = speedtest.Speedtest(secure=True)
    test.get_best_server()
    download = test.download()
    upload = test.upload(pre_allocate=False)
    return (
        f"DL: {_format_mbps(download)} | "
        f"UL: {_format_mbps(upload)} | "
        f"Ping: {test.results.ping:.2f}ms"
    )


async def _network_speed() -> str:
    try:
        return await asyncio.to_thread(_run_speedtest)
    except Exception as ex:
        logger.debug("Speedtest failed: %r", ex)
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
    network_speed_task = asyncio.create_task(_network_speed())
    db_latency_task = asyncio.create_task(_db_latency())
    calls_latency_task = asyncio.create_task(anon.ping())

    get_time = lambda s: (lambda r: (f"{r[-1]}, " if r[-1][:-4] != "0" else "") + ":".join(reversed(r[:-1])))([f"{v}{u}" for v, u in zip([s%60, (s//60)%60, (s//3600)%24, s//86400], ["s", "m", "h", "days"])])
    uptime = get_time(int(time.time() - boot))
    latency = round((time.perf_counter() - start) * 1000, 2)
    network_speed, db_latency, calls_latency = await asyncio.gather(
        network_speed_task,
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
    caption += (
        f"\n<b>Speedtest:</b> <code>{network_speed}</code>"
        f"\n<b>DB Latency:</b> <code>{db_latency}</code>"
    )
    await sent.edit_media(
        media=types.InputMediaPhoto(
            media=config.PING_IMG,
            caption=caption,
        ),
        reply_markup=buttons.ping_markup(m.lang["support"]),
    )
