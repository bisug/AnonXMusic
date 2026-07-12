# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import config, logger
from anony.helpers import Track, utils


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

    def _usable_file(self, filename: str | Path) -> bool:
        path = Path(filename)
        return path.exists() and path.is_file() and path.stat().st_size > 0

    def _api_enabled(self) -> bool:
        return bool(config.API_URL and config.API_KEY)

    def _cached_download(self, video_id: str, video: bool) -> str | None:
        exts = ["mp4"] if video else ["webm", "mp3", "m4a"]
        for ext in exts:
            filename = Path("downloads") / f"{video_id}.{ext}"
            if self._usable_file(filename):
                return str(filename)
        return None

    def cached_download(self, video_id: str, video: bool = False) -> str | None:
        return self._cached_download(video_id, video)

    def _api_filename(self, video_id: str, video: bool) -> Path:
        ext = "mp4" if video else "mp3"
        return Path("downloads") / f"{video_id}.{ext}"

    async def _download_api(self, video_id: str, video: bool = False) -> str | None:
        if not self._api_enabled():
            if not self.api_warned:
                self.api_warned = True
                logger.warning("API fallback is disabled; set API_URL and API_KEY.")
            return None

        filename = self._api_filename(video_id, video)
        if self._usable_file(filename):
            return str(filename)

        Path("downloads").mkdir(parents=True, exist_ok=True)
        tmpfile = filename.with_suffix(filename.suffix + ".part")
        timeout = aiohttp.ClientTimeout(total=600 if video else 300)
        params = {
            "url": video_id,
            "type": "video" if video else "audio",
            "api_key": config.API_KEY,
        }

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{config.API_URL}/download", params=params) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "API fallback failed for %s: HTTP %s",
                            video_id,
                            resp.status,
                        )
                        return None

                    content_type = resp.headers.get("Content-Type", "").lower()
                    if "application/json" in content_type or content_type.startswith("text/"):
                        message = (await resp.text())[:200]
                        logger.warning("API fallback failed for %s: %s", video_id, message)
                        return None

                    with open(tmpfile, "wb") as fw:
                        async for chunk in resp.content.iter_chunked(131072):
                            if chunk:
                                fw.write(chunk)

            if not self._usable_file(tmpfile):
                return None

            tmpfile.replace(filename)
            return str(filename)
        except Exception as ex:
            logger.warning("API fallback error for %s: %s", video_id, ex)
            return None
        finally:
            if tmpfile.exists() and not self._usable_file(filename):
                try:
                    tmpfile.unlink()
                except Exception:
                    pass

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

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception as ex:
            logger.warning("YouTube search failed for %r: %s", query, ex)
            return None
        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
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
            # video never aborts the whole playlist fetch.
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

    async def download(self, video_id: str, video: bool = False) -> str | None:
        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

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
            "no_warnings": True,
            "overwrites": False,
            "nocheckcertificate": True,
            "cookiefile": cookie,
            # Download up to 4 fragments concurrently — major speed boost
            # for DASH/HLS streams that are split into many small chunks.
            "concurrent_fragment_downloads": 4,
            # Fail fast on stalled connections instead of hanging indefinitely.
            "socket_timeout": 15,
            # Skip checking every format's availability before selecting;
            # trust the format string and only verify what we picked.
            "check_formats": "selected",
        }

        if video:
            ydl_opts = {
                **base_opts,
                # Prefer h264+aac in a single mp4 container when possible
                # (no post-merge step) then fall back to best available.
                "format": (
                    "bestvideo[height<=?720][width<=?1280][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]"
                    "/"
                    "bestvideo[height<=?720][width<=?1280][ext=mp4]+bestaudio"
                    "/"
                    "bestvideo[height<=?720]+bestaudio"
                    "/"
                    "best"
                ),
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                # Prefer native Opus/WebM (no transcoding), fall back to
                # any best-audio format so the download never fails silently.
                "format": "bestaudio[ext=webm][acodec=opus]/bestaudio[ext=m4a]/bestaudio/best",
            }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])
                except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError) as ex:
                    logger.warning("yt_dlp download failed for %s: %s", video_id, ex)
                    return None
                except Exception as ex:
                    logger.warning("Unexpected download error for %s: %s", video_id, ex)
                    return None
            return filename if self._usable_file(filename) else None

        downloaded = await asyncio.to_thread(_download)
        if downloaded:
            return downloaded
        return None
