# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of Melody


import os
import re
import time
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from melody import config, logger
from melody.core import providers
from melody.helpers import Track, utils


class _YDLLogger:
    """Forward yt-dlp warnings/errors to the app logger."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        logger.warning("yt_dlp: %s", msg)

    def error(self, msg):
        logger.error("yt_dlp: %s", msg)


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "melody/cookies"
        self.warned = False
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )
        # Same-id requests share one download task.
        self._inflight: dict[str, asyncio.Task] = {}
        # Waiter count per id; zero aborts the download via progress hook.
        self._waiters: dict[str, int] = {}

    def _usable_file(self, filename: str | Path) -> bool:
        path = Path(filename)
        # yt-dlp downloads to `<name>.part` (and writes a `<name>.ytdl` sidecar)
        # before renaming; those are incomplete and must never be treated as a
        # finished download or a concurrent request plays a truncated file.
        if path.suffix in (".part", ".ytdl"):
            return False
        return path.exists() and path.is_file() and path.stat().st_size > 0

    def _api_enabled(self) -> bool:
        return bool(config.API_URL and config.API_KEY)

    @staticmethod
    def _mtime(path: Path) -> float:
        # File can be unlinked by eviction between glob() and stat().
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    def _cached_download(self, video_id: str, video: bool) -> str | None:
        # Scan all extensions; yt-dlp may write mp4/webm/m4a/mkv.
        candidates = sorted(
            Path("downloads").glob(f"{video_id}.*"),
            key=self._mtime,
            reverse=True,
        )
        for path in candidates:
            if self._usable_file(path):
                return str(path)
        return None

    def cached_download(self, video_id: str, video: bool = False) -> str | None:
        return self._cached_download(video_id, video)

    def _evict_downloads(
        self, max_bytes: int = 4 * 1024**3, min_age: float = 3600
    ) -> None:
        """Cap downloads/ and cache/ dirs by size, oldest-first.

        shortcut: LRU by mtime with 1h floor, not ref-counting.
        """
        for dirname in ("downloads", "cache"):
            self._evict_dir(Path(dirname), max_bytes, min_age)

    def _evict_dir(
        self, downloads: Path, max_bytes: int, min_age: float
    ) -> None:
        if not downloads.is_dir():
            return

        files = []
        total = 0
        for p in downloads.iterdir():
            if not p.is_file():
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            files.append((p, st.st_mtime, st.st_size))
            total += st.st_size

        if total <= max_bytes:
            return

        now = time.time()
        files.sort(key=lambda t: t[1])  # oldest first
        for p, mtime, size in files:
            if total <= max_bytes:
                break
            if now - mtime < min_age:
                continue
            try:
                p.unlink()
                total -= size
            except OSError as ex:
                logger.warning("Failed to evict %s: %s", p, ex)

    async def _download_api(self, video_id: str, video: bool = False) -> str | None:
        """Try each download-API provider in order; None if all miss."""
        for name, provider in (
            ("ShrutiBots", providers.shrutibots),
            ("OneGrab", providers.onegrab),
            ("NexGen", providers.nexgen),
        ):
            downloaded = await provider(video_id, video=video)
            if downloaded:
                return downloaded
            logger.debug("Provider %s missed for %s", name, video_id)
        return None

    def get_cookies(self):
        if not self.checked:
            for file in os.listdir(self.cookie_dir):
                if file.endswith(".txt"):
                    self.cookies.append(f"{self.cookie_dir}/{file}")
            self.checked = True
        if not self.cookies:
            if not self.warned and not self._api_enabled():
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(f"{self.cookie_dir}/{name}.txt", "wb") as fw:
                        fw.write(await resp.read())
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    def _pot_extractor_args(self) -> dict:
        """yt-dlp extractor_args with PO token provider (POT_BASE_URL; empty disables)."""
        args = {
            "youtube": {
                "player_client": ["visionos", "tv_downgraded"],
            }
        }
        if config.POT_BASE_URL:
            args["youtubepot-bgutilhttp"] = {"base_url": config.POT_BASE_URL}
        return args

    async def stream_url(self, video_id: str, video: bool = False) -> str | None:
        """Resolve live stream to HLS URL(s); video mode returns "video|audio"."""
        url = self.base + video_id
        cookie = self.get_cookies()
        opts = {
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "logger": _YDLLogger(),
            "cookiefile": cookie,
            "socket_timeout": 15,
            "retries": 5,
            "extractor_args": self._pot_extractor_args(),
            # Live HLS: best variant only; master playlist triggers parallel
            # fetches that googlevideo rate-limits.
            "format": "bv*[height<=?720]+ba/b" if video else "ba/b",
        }

        def _extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info or not info.get("is_live"):
                return None
            requested = info.get("requested_formats") or [info]
            urls = [f.get("url") for f in requested if f.get("url")]
            if not urls:
                return None
            return "|".join(urls)

        try:
            return await asyncio.to_thread(_extract)
        except Exception as ex:
            logger.warning("Live stream URL extraction failed for %s: %s", video_id, ex)
            return None

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            # with_live so live URLs resolve to the live video, not a VOD.
            _search = VideosSearch(query, limit=1, with_live=True)
            results = await _search.next()
        except Exception as ex:
            logger.warning("YouTube search failed for %r: %s", query, ex)
            return None
        if results and results["result"]:
            data = results["result"][0]
            title = data.get("title") or "Unknown"
            thumbs = data.get("thumbnails") or []
            thumbnail = thumbs[-1].get("url", "").split("?")[0] if thumbs else None
            # Live entries have no duration and no view count.
            is_live = data.get("duration") is None
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration="LIVE" if is_live else data.get("duration"),
                duration_sec=0 if is_live else utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=title[:25],
                thumbnail=thumbnail,
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short") or "",
                video=video,
                is_live=is_live,
            )
        return None

    async def playlist(
        self,
        limit: int,
        user: str,
        url: str,
        video: bool,
        shuffle: bool = False,
    ) -> list[Track]:
        tracks = []
        try:
            plist = await Playlist.get(url)
        except Exception as ex:
            logger.warning("Failed to fetch playlist %s: %s", url, ex)
            return tracks

        for data in plist.get("videos", []):
            # Skip bad entries individually; a live entry would hang the queue.
            vid = data.get("id")
            title = data.get("title")
            duration = data.get("duration")
            link = data.get("link")
            if not (vid and title and duration and link):
                continue

            try:
                duration_sec = utils.to_seconds(duration)
            except (ValueError, AttributeError):
                continue

            thumbs = data.get("thumbnails") or []
            thumbnail = thumbs[-1].get("url", "").split("?")[0] if thumbs else None

            tracks.append(
                Track(
                    id=vid,
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=duration,
                    duration_sec=duration_sec,
                    title=title[:25],
                    thumbnail=thumbnail,
                    url=link.split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
            )
            if len(tracks) >= limit:
                break

        if shuffle:
            random.shuffle(tracks)
        return tracks

    async def download(
        self, video_id: str, video: bool = False, prefetch: bool = False
    ) -> str | None:
        url = self.base + video_id

        cached = self._cached_download(video_id, video)
        if cached:
            return cached

        if self._api_enabled():
            downloaded = await self._download_api(video_id, video=video)
            if downloaded:
                return downloaded

        cookie = self.get_cookies()

        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            # Route warnings/errors to the app logger instead of swallowing
            # them, so merge/format problems are visible (no no_warnings).
            "logger": _YDLLogger(),
            "overwrites": False,
            "cookiefile": cookie,
            # Explicit retry budget for an unattended bot (defaults are high).
            "retries": 5,
            "fragment_retries": 5,
            "file_access_retries": 3,
            # 4 concurrent fragments speed up chunked streams; prefetch uses 1
            # to avoid stuttering live playback.
            "concurrent_fragment_downloads": 1 if prefetch else 4,
            "socket_timeout": 15,
            # Trust the format selector; avoids an extra RTT per stream.
            "check_formats": False,
            # YouTube forces SABR on most clients; visionos returns full
            # formats without a token, tv_downgraded covers age/region gates.
            "extractor_args": self._pot_extractor_args(),
        }

        if video:
            ydl_opts = {
                **base_opts,
                # 720p h264/aac merged to mp4.
                "format": "bv*[height<=?720]+ba/b",
                "format_sort": ["vcodec:h264", "acodec:aac", "ext:mp4"],
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                # Native Opus/WebM first (no transcoding), else best audio.
                "format": "ba/b",
                "format_sort": ["acodec:opus", "ext:webm"],
            }

        # Hook aborts the download when the last waiter cancels (skip/stop).
        def _progress_hook(_status):
            if self._waiters.get(video_id, 0) <= 0:
                raise yt_dlp.utils.DownloadCancelled()

        opts = {**ydl_opts, "progress_hooks": [_progress_hook]}

        def _download():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                except yt_dlp.utils.DownloadCancelled:
                    return None
                except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as ex:
                    logger.warning("yt_dlp download failed for %s: %s", video_id, ex)
                    return None
                except Exception as ex:
                    logger.warning("Unexpected download error for %s: %s", video_id, ex)
                    return None
            # Use yt-dlp's reported path; scan the dir only as fallback.
            requested = (info or {}).get("requested_downloads") or []
            path = None
            if requested:
                candidate = requested[0].get("filepath")
                if candidate and self._usable_file(candidate):
                    path = str(candidate)
            if path is None:
                path = self._cached_download(video_id, video)
            if path:
                self._evict_downloads()
            return path

        # Same-id requests share one task; shield keeps it alive for other
        # waiters when one caller cancels.
        self._waiters[video_id] = self._waiters.get(video_id, 0) + 1
        try:
            task = self._inflight.get(video_id)
            if task is None:
                task = asyncio.ensure_future(asyncio.to_thread(_download))
                self._inflight[video_id] = task
                task.add_done_callback(
                    lambda t, v=video_id: self._inflight.pop(v, None)
                    if self._inflight.get(v) is t
                    else None
                )
            # shield: a cancelled caller must not kill the shared download.
            return await asyncio.shield(task)
        finally:
            self._waiters[video_id] = self._waiters.get(video_id, 1) - 1
            if self._waiters.get(video_id, 0) <= 0:
                self._waiters.pop(video_id, None)
