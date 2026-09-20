# Playback-Pipeline

Order per track (`melody/core/youtube.py`, providers in `melody/core/providers.py`):

1. **Cache** — `downloads/<video_id>.*` reused if non-empty (yt-dlp `.part`/`.ytdl` artifacts are ignored); dirs evicted oldest-first past ~4 GB / 1 h min age.
2. **ShrutiBots** (`API_URL`+`API_KEY`) → 3. **OneGrab** (`ONEGRAB_*`) → 4. **NexGen** (`NEXGEN_*`) — each streams to a `.part` file, rejects JSON/text error bodies, then renames on success.
5. **yt-dlp** — audio prefers native Opus/WebM (`ba/b`), video prefers H264+AAC in MP4; concurrent same-id downloads de-duplicated, cancelled when the last waiter leaves. Uses `melody/cookies/*.txt` when present.
6. **Cookies** — `COOKIES_URL` entries (batbin.me only) are fetched at startup into `melody/cookies/`.
7. **PO tokens** — if `POT_BASE_URL` set, `bgutil-ytdlp-pot-provider` makes requests look like a real browser.

Prefetch: next track downloads while current plays (`TgCall._prefetch`); skip/stop cancels the waiter so bandwidth isn't wasted.


## After the queue empties: autoplay

`TgCall.play_next` pops the queue; when it is empty and autoplay is enabled for the chat (`/autoplay`, stored in `chatsdb.autoplay`):

1. `YouTube.related()` searches the current track's title (`VideosSearch`, 10 results, live disabled).
2. `pick_candidate()` picks a **random** playable result — the current video id, live entries, and tracks over `DURATION_LIMIT` are excluded.
3. The pick is downloaded and played like a normal next track, so the loop repeats until `/autoplay off` or `/stop`.
4. Nothing found (or a download failure) ends playback normally via `stop()`.

## Now-playing message: rich panel

With `RICH_UI=True` (default), `play_media` replaces the placeholder message with a rich message (`melody/helpers/_rich.py`): photo block, linked title, meta line, a progress-bar row, and styled Pause/Resume · Replay · Skip · Stop buttons. The buttons reuse the same `controls …` callback data as the classic keyboard, so admin checks are identical.

- The `update_timer` background task re-renders the panel every 12 s with the current progress.
- Pause/resume callbacks re-render instead of rewriting text; tapping the progress row answers with `MM:SS / duration`.
- If the chat forbids photos, the panel is retried without the picture block; if rich messages fail entirely, the classic text + inline-keyboard UI is used. `Media.rich_ui` marks which UI is live.
