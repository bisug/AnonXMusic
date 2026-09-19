# Playback-Pipeline

Order per track (`melody/core/youtube.py`, providers in `melody/core/providers.py`):

1. **Cache** — `downloads/<video_id>.*` reused if non-empty; dirs evicted oldest-first past ~4 GB / 1 h min age.
2. **yt-dlp** — audio prefers native Opus/WebM (`ba/b`), video prefers H264+AAC in MP4; concurrent same-id downloads de-duplicated, cancelled when last waiter leaves.
3. **ShrutiBots** (`API_URL`+`API_KEY`) → 4. **OneGrab** (`ONEGRAB_*`) → 5. **NexGen** (`NEXGEN_*`) — each streams to a `.part` file, rejects JSON/text error bodies, then renames on success.
6. **Cookie-aware retry** — age/region-gated videos retried with Netscape cookies from `COOKIES_URL` / `melody/cookies/*.txt`.
7. **PO tokens** — if `POT_BASE_URL` set, `bgutil-ytdlp-pot-provider` makes requests look like a real browser.

Prefetch: next track downloads while current plays (`TgCall._prefetch`); skip/stop cancels the waiter so bandwidth isn't wasted.
