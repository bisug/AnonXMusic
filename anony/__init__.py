# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import time
import asyncio
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s: %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("log.txt", maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("ntgcalls").setLevel(logging.CRITICAL)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


__version__ = "3.0.3"

from config import Config

config = Config()
config.check()
tasks: list[asyncio.Task] = []
_stop_lock: asyncio.Lock | None = None
_stopped = False
_shutting_down = False
boot = time.time()


def is_shutting_down() -> bool:
    """Return True once the shutdown sequence has begun."""
    return _shutting_down

from anony.core.bot import Bot
app = Bot()

from anony.core.dir import ensure_dirs
ensure_dirs()

from anony.core.userbot import Userbot
userbot = Userbot()

from anony.core.mongo import MongoDB
db = MongoDB()

from anony.core.lang import Language
lang = Language()

from anony.core.telegram import Telegram
from anony.core.youtube import YouTube
tg = Telegram()
yt = YouTube()

from anony.helpers import Queue, Thumbnail
queue = Queue()
thumb = Thumbnail()

from anony.core.calls import TgCall
anon = TgCall()


def _get_stop_lock() -> asyncio.Lock:
    global _stop_lock

    if _stop_lock is None:
        _stop_lock = asyncio.Lock()
    return _stop_lock


async def _cancel_tasks() -> None:
    current_task = asyncio.current_task()
    pending = [
        task
        for task in dict.fromkeys(tasks)
        if task is not current_task and not task.done()
    ]
    tasks.clear()

    if not pending:
        return

    logger.info("Cancelling %s background task(s)...", len(pending))
    for task in pending:
        task.cancel()

    results = await asyncio.gather(*pending, return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException) and not isinstance(
            result, asyncio.CancelledError
        ):
            logger.warning("Background task failed during shutdown: %r", result)


async def _run_cleanup(
    name: str,
    closer,
    *,
    ignore_cleanup_errors: bool,
    timeout: float = 30,
) -> None:
    try:
        await asyncio.wait_for(closer(), timeout=timeout)
    except asyncio.CancelledError:
        raise
    except Exception as ex:
        if ignore_cleanup_errors:
            logger.debug("Ignored %s cleanup error: %r", name, ex)
        else:
            logger.exception("Error while stopping %s.", name)


async def stop(ignore_cleanup_errors: bool = False) -> None:
    global _stopped, _shutting_down

    async with _get_stop_lock():
        if _stopped:
            return

        _shutting_down = True
        logger.info("Stopping...")
        await _cancel_tasks()

        cleaners = (
            ("telegram downloads", tg.close),
            ("voice calls", anon.exit),
            ("bot", app.exit),
            ("assistants", userbot.exit),
            ("database", db.close),
            ("thumbnails", thumb.close),
        )

        # Hard deadline: the entire cleanup must finish within 60 seconds.
        try:
            async with asyncio.timeout(60):
                for name, closer in cleaners:
                    await _run_cleanup(
                        name,
                        closer,
                        ignore_cleanup_errors=ignore_cleanup_errors,
                    )
        except TimeoutError:
            logger.warning("Shutdown timed out after 60 s; forcing exit.")

        _stopped = True
        logger.info("Stopped.\n")
