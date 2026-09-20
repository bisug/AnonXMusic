# Architecture

One Python process, three Telegram clients (the bot plus up to three assistant userbots), one MongoDB. Every connection is outbound: Telegram MTProto, MongoDB, and media sources — there is no inbound HTTP server.

![Melody architecture](https://raw.githubusercontent.com/bisug/Melody/master/docs/architecture.svg)

## Module map

| Layer | Files | Responsibility |
|---|---|---|
| Plugins | `melody/plugins/` (24 modules, auto-discovered, sorted import) | Command handlers, callback queries, watchers (VC start/end, new members, channel posts) |
| Telegram I/O | `core/bot.py`, `core/userbot.py`, `core/telegram.py` | kurigram bot client, assistant string sessions, TG media downloads (200 MB cap, cancel events) |
| Playback | `core/calls.py` (`TgCall`) | `play_media` → `MediaStream` (ffmpeg args for reconnect/seek) → `StreamEnded` → `play_next`; loop counter, seek/replay, autoplay hook, prefetch, stop/leave on VC close |
| Media sourcing | `core/youtube.py`, `core/providers.py` | `py_yt` search, `related()` for autoplay, yt-dlp with PO tokens/cookies, HTTP fallback chain, LRU cache eviction (~4 GB) |
| State | `core/mongo.py` | Users, chats, per-chat settings (autoplay, channel play, play mode, thumbnails, language), sudo/blacklist, assistant slots |
| UX | `helpers/_rich.py`, `helpers/_inline.py`, `core/lang.py`, `helpers/_thumbnails.py` | Rich now-playing panel, inline keyboards, 14 JSON locales with English fallback, generated covers |
| Guards | `helpers/_play.py`, `helpers/_admins.py` | SSRF check for stream URLs, assistant join flow, admin cache with 30 min TTL |

## Playback flow

1. `/play` → `checkUB` validates chat/admins, ensures the assistant joined → track resolved (search, link, playlist, Telegram reply, or m3u8).
2. `play_media` streams via the assistant's `pytgcalls` client and publishes the now-playing panel (rich or classic).
3. Background tasks: `track_time` (per-second position), `update_timer` (progress bar), `vc_watcher` (auto-end), `auto_leave`.
4. `StreamEnded` → `play_next` pops the queue → empty queue + autoplay → `YouTube.related()` → next track; otherwise `stop()` cleans up and leaves.
