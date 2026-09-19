# Playback-Pipeline

Order per track (`melody/core/youtube.py`, providers in `melody/core/providers.py`):

1. **Cache** — `downloads/<video_id>.*` reused if non-empty (yt-dlp `.part`/`.ytdl` artifacts are ignored); dirs evicted oldest-first past ~4 GB / 1 h min age.
2. **ShrutiBots** (`API_URL`+`API_KEY`) → 3. **OneGrab** (`ONEGRAB_*`) → 4. **NexGen** (`NEXGEN_*`) — each streams to a `.part` file, rejects JSON/text error bodies, then renames on success.
5. **yt-dlp** — audio prefers native Opus/WebM (`ba/b`), video prefers H264+AAC in MP4; concurrent same-id downloads de-duplicated, cancelled when the last waiter leaves. Uses `melody/cookies/*.txt` when present.
6. **Cookies** — `COOKIES_URL` entries (batbin.me only) are fetched at startup into `melody/cookies/`.
7. **PO tokens** — if `POT_BASE_URL` set, `bgutil-ytdlp-pot-provider` makes requests look like a real browser.

Prefetch: next track downloads while current plays (`TgCall._prefetch`); skip/stop cancels the waiter so bandwidth isn't wasted.
