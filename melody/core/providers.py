# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody

"""HTTP fallback providers: (video_id, video) -> local path or None."""

import asyncio
import ipaddress
import socket
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from melody import config, logger

CHUNK = 131072
MAX_MEDIA_BYTES = 2 * 1024**3
WATCH_BASE = "https://www.youtube.com/watch?v="


async def _public_url(url: str) -> bool:
    """Reject provider URLs that resolve to non-public addresses."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        infos = await asyncio.to_thread(
            socket.getaddrinfo, parsed.hostname, port, 0, socket.SOCK_STREAM
        )
        for info in infos:
            addr = ipaddress.ip_address(info[4][0])
            if (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_reserved
                or addr.is_multicast
                or addr.is_unspecified
            ):
                return False
        return True
    except (OSError, ValueError):
        return False


def _filename(video_id: str, video: bool) -> Path:
    ext = "mp4" if video else "mp3"
    mode = "video" if video else "audio"
    return Path("downloads") / f"{video_id}-{mode}.{ext}"


def _usable(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _discard_partial(tmpfile: Path, filename: Path) -> None:
    """Drop an incomplete .part file once a download fails."""
    if tmpfile.exists() and not _usable(filename):
        with suppress(OSError):
            tmpfile.unlink()


async def _stream_to_file(
    resp: aiohttp.ClientResponse, tmpfile: Path
) -> bool:
    """Stream a bounded response body to tmpfile; False on error bodies."""
    content_type = resp.headers.get("Content-Type", "").lower()
    if "application/json" in content_type or content_type.startswith("text/"):
        message = (await resp.content.read(200)).decode(errors="replace")
        logger.warning("API fallback error body: %s", message)
        return False
    content_length = resp.content_length
    if content_length is not None and content_length > MAX_MEDIA_BYTES:
        logger.warning("API fallback response is too large: %s bytes", content_length)
        return False
    Path("downloads").mkdir(parents=True, exist_ok=True)
    total = 0
    with open(tmpfile, "wb") as fw:
        async for chunk in resp.content.iter_chunked(CHUNK):
            total += len(chunk)
            if total > MAX_MEDIA_BYTES:
                fw.close()
                return False
            fw.write(chunk)
    return _usable(tmpfile)


async def _finish(tmpfile: Path, filename: Path) -> str | None:
    if _usable(tmpfile):
        tmpfile.replace(filename)
        return str(filename)
    return None


async def _fetch_json(
    session: aiohttp.ClientSession, url: str, **kw
) -> dict | None:
    """GET a JSON document; None (with a log) on non-200/bad JSON."""
    async with session.get(url, allow_redirects=False, **kw) as resp:
        if resp.status != 200:
            logger.warning("API fallback %s: HTTP %s", urlparse(url).hostname, resp.status)
            return None
        try:
            return await resp.json()
        except Exception as ex:
            logger.warning("API fallback %s: bad JSON: %s", url, ex)
            return None


async def shrutibots(video_id: str, video: bool = False) -> str | None:
    """Primary fallback: GET /download streams the file directly."""
    if not (config.API_URL and config.API_KEY):
        return None

    filename = _filename(video_id, video)
    if _usable(filename):
        return str(filename)

    tmpfile = filename.with_suffix(filename.suffix + ".part")
    timeout = aiohttp.ClientTimeout(total=600 if video else 300)
    params = {
        "url": video_id,
        "type": "video" if video else "audio",
        "api_key": config.API_KEY,
    }
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{config.API_URL}/download", params=params
            ) as resp:
                if resp.status != 200:
                    logger.warning(
                        "ShrutiBots failed for %s: HTTP %s", video_id, resp.status
                    )
                    return None
                if not await _stream_to_file(resp, tmpfile):
                    return None
        return await _finish(tmpfile, filename)
    except Exception as ex:
        logger.warning("ShrutiBots error for %s: %s", video_id, ex)
        return None
    finally:
        _discard_partial(tmpfile, filename)


async def onegrab(video_id: str, video: bool = False) -> str | None:
    """Second fallback: /api/track returns {cdnurl} to fetch separately."""
    if not config.ONEGRAB_KEY:
        return None

    filename = _filename(video_id, video)
    if _usable(filename):
        return str(filename)

    tmpfile = filename.with_suffix(filename.suffix + ".part")
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            data = await _fetch_json(
                session,
                f"{config.ONEGRAB_URL}/api/track",
                params={
                    "url": f"{WATCH_BASE}{video_id}",
                    "video": "true" if video else "false",
                },
                headers={"X-API-Key": config.ONEGRAB_KEY},
            )
        cdnurl = (data or {}).get("cdnurl")
        if not cdnurl or not await _public_url(cdnurl):
            logger.warning("OneGrab: invalid cdnurl for %s", video_id)
            return None

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=600 if video else 300)
        ) as session:
            async with session.get(cdnurl, allow_redirects=False) as resp:
                if resp.status != 200:
                    logger.warning(
                        "OneGrab CDN failed for %s: HTTP %s", video_id, resp.status
                    )
                    return None
                if not await _stream_to_file(resp, tmpfile):
                    return None
        return await _finish(tmpfile, filename)
    except Exception as ex:
        logger.warning("OneGrab error for %s: %s", video_id, ex)
        return None
    finally:
        _discard_partial(tmpfile, filename)


async def nexgen(video_id: str, video: bool = False) -> str | None:
    """Third fallback: separate audio/video hosts, same key.

    Audio streams directly; video needs a JSON link lookup first.
    """
    if not config.NEXGEN_KEY:
        return None

    filename = _filename(video_id, video)
    if _usable(filename):
        return str(filename)

    tmpfile = filename.with_suffix(filename.suffix + ".part")
    try:
        timeout = aiohttp.ClientTimeout(total=600 if video else 300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if video:
                data = await _fetch_json(
                    session,
                    f"{config.NEXGEN_VIDEO_URL}/video/{video_id}",
                    params={"api": config.NEXGEN_KEY},
                )
                link = (data or {}).get("link")
                if not link or (data or {}).get("status") != "done" or not await _public_url(link):
                    logger.warning(
                        "NexGen video not ready for %s: %s", video_id, data
                    )
                    return None
                stream_url = link
            else:
                stream_url = (
                    f"{config.NEXGEN_AUDIO_URL}/stream/{video_id}"
                    f"?api={config.NEXGEN_KEY}"
                )

            async with session.get(stream_url, allow_redirects=False) as resp:
                if resp.status != 200:
                    logger.warning(
                        "NexGen stream failed for %s: HTTP %s",
                        video_id,
                        resp.status,
                    )
                    return None
                if not await _stream_to_file(resp, tmpfile):
                    return None
        return await _finish(tmpfile, filename)
    except Exception as ex:
        logger.warning("NexGen error for %s: %s", video_id, ex)
        return None
    finally:
        _discard_partial(tmpfile, filename)
