# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import time
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import config, logger
from anony.core import providers
from anony.helpers import Track, utils


class _YDLLogger:
    """Route yt-dlp output to the app logger.

    Debug/info are dropped (too noisy), but warnings — e.g. 'incompatible
    for merge -> mkv' or 'requested format not available' — reach the log so
    format/merge problems are never silent.
    """

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
        self.cookie_dir = "anony/cookies"
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
        self.api_warned = False
        # In-flight downloads keyed by video id, so concurrent requests for
        # the same id share one download instead of colliding on the file.
        self._inflight: dict[str, asyncio.Task] = {}
        # Live waiter count per in-flight id. When it drops to zero (every
        # caller cancelled), the yt-dlp progress hook aborts the worker thread.
        self._waiters: dict[str, int] = {}

    def _usable_file(self, filename: str | Path) -> bool:
        path = Path(filename)
        return path.exists() and path.is_file() and path.stat().st_size > 0

    def _api_enabled(self) -> bool:
        return bool(config.API_URL and config.API_KEY)

    def _cached_download(self, video_id: str, video: bool) -> str | None:
        # Scan every extension for the id rather than a hardcoded whitelist.
        # yt-dlp may write .mp4/.webm/.m4a/.mkv/... depending on the chosen
        # format and merge; guessing extensions hid real files and caused a
        # re-download loop. Return the most recently written usable match.
        candidates = sorted(
            Path("downloads").glob(f"{video_id}.*"),
            key=lambda p: p.stat().st_mtime,
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
        """Cap the downloads/ and cache/ dirs by total size, oldest-first.

        cache/ holds generated thumbnails (~200KB each) that were previously
        never evicted — unbounded disk growth over months of uptime.

        ponytail: LRU by mtime with a 1h floor — files touched within the
        last hour are skipped so an in-progress or actively-streamed track is
        never deleted (max track length is bounded by DURATION_LIMIT). If the
        floor ever proves unsafe, upgrade to ref-counting against active calls.
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

    def _api_filename(self, video_id: str, video: bool) -> Path:
        ext = "mp4" if video else "mp3"
        return Path("downloads") / f"{video_id}.{ext}"

    async def _download_api(self, video_id: str, video: bool = False) -> str | None:
        """Try every configured download-API provider, in order.

        Providers live in anony/core/providers.py; each returns a local file
        path or None, so a failing provider just falls through to the next.
        """
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
        """yt-dlp extractor_args with the PO token provider wired in.

        The bgutil plugin (bgutil-ytdlp-pot-provider, installed as a yt-dlp
        plugin via pyproject) fetches proof-of-origin tokens from an HTTP
        server. With a valid POT, YouTube treats requests like a real
        browser — this is the main defense against "confirm you're not a
        bot" walls on datacenter IPs (Heroku/Render/VPS).

        POT_BASE_URL points at the provider server; empty disables it and
        the plugin stays dormant (yt-dlp just skips unavailable providers).
        """
        args = {
            "youtube": {
                "player_client": ["visionos", "tv_downgraded"],
            }
        }
        if config.POT_BASE_URL:
            args["youtubepot-bgutilhttp"] = {"base_url": config.POT_BASE_URL}
        return args

    async def stream_url(self, video_id: str, video: bool = False) -> str | None:
        """Resolve a live stream to its HLS URL(s) without downloading.

        Live HLS can't be downloaded to a file (it never ends), so the URL is
        handed straight to ffmpeg. YouTube live HLS is demuxed: video and
        audio are separate variant playlists. Returns the audio variant URL,
        or a "video|audio" pair for video mode (play_media splits them).
        """
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
            # Live HLS only: pick the best audio variant, or the <=720p video
            # variant + best audio for video mode. The master playlist is NOT
            # used — ffmpeg fetches all 7 variant playlists in parallel and
            # googlevideo rate-limits the keepalive requests.
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
            # with_live=True so direct live-stream URLs resolve to the live
            # video instead of a random related VOD (py_yt's scraper search
            # can't see live results otherwise). Live entries come back with
            # duration=None / viewCount=None.
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
            # Skip private/deleted/live entries individually so one bad
            # video never aborts the whole playlist fetch. Live entries are
            # skipped too: a live stream inside a playlist would hang the
            # sequential queue download forever.
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
            # Download up to 4 fragments concurrently — major speed boost
            # for DASH/HLS streams that are split into many small chunks.
            # Prefetch (next-track, runs *during* live playback) drops to 1 so
            # it can't parallel-hammer CPU/IO/bandwidth and stutter the encoder.
            "concurrent_fragment_downloads": 1 if prefetch else 4,
            # Fail fast on stalled connections instead of hanging indefinitely.
            "socket_timeout": 15,
            # Don't pre-test every selected format; trust the selector and
            # only download what we picked. Avoids an extra RTT per stream
            # (and a transient 403/429 dropping a working format to /best).
            "check_formats": False,
            # YouTube forces SABR on most clients, so formats come back
            # without a URL and the download silently fails. yt-dlp 2026.6+
            # removed android_sdkless; visionos is the new default no-token
            # client (full format table, no PO token, no JS player needed).
            # tv_downgraded is the cookie-aware fallback for age/region
            # restricted videos.
            "extractor_args": self._pot_extractor_args(),
        }

        if video:
            ydl_opts = {
                **base_opts,
                # Cap at 720p, prefer h264/aac in an mp4 container; yt-dlp
                # picks the best 720p h264 stream and merges to mp4. The
                # real written path is resolved via extract_info below, so
                # we never guess the extension.
                "format": "bv*[height<=?720]+ba/b",
                "format_sort": ["vcodec:h264", "acodec:aac", "ext:mp4"],
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                # Prefer native Opus/WebM (no transcoding), fall back to any
                # best-audio format so the download never fails silently.
                "format": "ba/b",
                "format_sort": ["acodec:opus", "ext:webm"],
            }

        # Cooperative cancel: a to_thread worker can't be cancelled from the
        # loop, so this hook (fired between fragments) aborts the download the
        # moment the last waiter goes away — no wasted bandwidth on skipped
        # tracks. Reads a plain dict int; the GIL makes that safe cross-thread.
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
            # Ask yt-dlp exactly what it wrote instead of guessing the
            # extension — audio may fall back to .mp4, video merges may emit
            # .mkv, etc. Fall back to a directory scan only if the info dict
            # doesn't carry the path (older/edge extractor results).
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

        # De-duplicate concurrent downloads of the same id (background play
        # task + next-track prefetch can both fire for one video). Whoever
        # arrives first owns the download; the rest await the same task.
        # A per-id waiter count drives the cancel hook above.
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
            # shield: if this caller is cancelled (skip/queue change) the
            # shared download keeps running for any other waiter instead of
            # being torn down mid-flight.
            return await asyncio.shield(task)
        finally:
            self._waiters[video_id] = self._waiters.get(video_id, 1) - 1
            if self._waiters.get(video_id, 0) <= 0:
                self._waiters.pop(video_id, None)
