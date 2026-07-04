# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
from contextlib import suppress
from io import BytesIO
from pathlib import Path

import aiohttp
from PIL import (Image, ImageDraw, ImageEnhance,
                 ImageFilter, ImageFont, ImageOps)

from anony import config
from anony.helpers import Track


class Thumbnail:
    def __init__(self):
        self.rect = (914, 514)
        self.size = (1280, 720)
        self.fill = (255, 255, 255)
        self.mask = Image.new("L", self.rect, 0)
        ImageDraw.Draw(self.mask).rounded_rectangle(
            (0, 0, self.rect[0], self.rect[1]),
            radius=15,
            fill=255,
        )
        self.font1 = ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 30)
        self.font2 = ImageFont.truetype("anony/helpers/Inter-Light.ttf", 30)
        self.session: aiohttp.ClientSession | None = None
        self.timeout = aiohttp.ClientTimeout(total=8, connect=3, sock_read=5)
        self.pending: dict[str, asyncio.Task[str]] = {}

    async def start(self) -> None:
        self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError, Exception):
                await asyncio.wait_for(asyncio.shield(task), timeout=5)
        self.pending.clear()
        if self.session and not self.session.closed:
            await self.session.close()

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        if not song.thumbnail:
            return config.DEFAULT_THUMB

        cached = self.cached_path(song.id)
        if cached:
            return cached

        task = self.pending.get(song.id)
        if not task:
            task = asyncio.create_task(self._generate(song, size))
            self.pending[song.id] = task

        try:
            return await task
        finally:
            if self.pending.get(song.id) is task:
                self.pending.pop(song.id, None)

    def cached_path(self, song_id: str) -> str | None:
        for suffix in ("jpg", "png"):
            path = Path("cache") / f"{song_id}.{suffix}"
            if path.exists():
                return str(path)
        return None

    async def download_thumb(self, url: str) -> bytes:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def _generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            output = Path("cache") / f"{song.id}.jpg"
            data = await self.download_thumb(song.thumbnail)
            await asyncio.to_thread(self.render, data, output, song, size)
            return str(output)
        except Exception:
            return config.DEFAULT_THUMB

    def render(
        self,
        data: bytes,
        output: Path,
        song: Track,
        size: tuple[int, int],
    ) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(BytesIO(data)) as source:
            source = ImageOps.exif_transpose(source).convert("RGBA")
            background = ImageOps.fit(
                source,
                size,
                method=Image.Resampling.BILINEAR,
                centering=(0.5, 0.5),
            )
            card = ImageOps.fit(
                source,
                self.rect,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )

        image = ImageEnhance.Brightness(
            background.filter(ImageFilter.GaussianBlur(18))
        ).enhance(.40)
        card.putalpha(self.mask)
        image.paste(card, (183, 30), card)

        channel = (song.channel_name or "")[:25]
        view_count = song.view_count or ""
        title = (song.title or "")[:50]
        duration = song.duration or "00:00"

        draw = ImageDraw.Draw(image)
        draw.text(
            xy=(50, 560),
            text=f"{channel} | {view_count}",
            font=self.font2,
            fill=self.fill,
        )
        draw.text((50, 600), title, font=self.font1, fill=self.fill)
        draw.text((40, 650), "0:01", font=self.font1, fill=self.fill)
        draw.line([(140, 670), (1160, 670)], fill=self.fill, width=5, joint="curve")
        draw.text((1185, 650), duration, font=self.font1, fill=self.fill)

        temp = output.with_name(f"{output.stem}.tmp{output.suffix}")
        image.convert("RGB").save(
            temp,
            format="JPEG",
            quality=85,
            subsampling=2,
        )
        temp.replace(output)
