# Configuration

Source of truth: `config.py`. Copy `sample.env` → `.env`; on hosts set real env vars instead.

## Required

| Var | Description |
|---|---|
| `API_ID`, `API_HASH` | From https://my.telegram.org/apps |
| `BOT_TOKEN` | From @BotFather |
| `MONGO_URL` | MongoDB connection string (cloud.mongodb.com) |
| `LOGGER_ID` | Log group/channel ID; bot must be admin there |
| `OWNER_ID` | Owner user ID |
| `SESSION` | Pyrogram v2 string session (@StringFatherBot); assistants 2–3 via `SESSION2`/`SESSION3` |

## Optional (tuning)

| Var | Default | Description |
|---|---|---|
| `SUPPORT_CHANNEL`, `SUPPORT_CHAT` | `https://t.me/SuMelodyVibes` | URL, @username, username, or numeric ID; private IDs need bot admin + invite-link permission |
| `DURATION_LIMIT` | `60` (minutes) | Max track length, stored as seconds |
| `QUEUE_LIMIT` | `20` | Max queued tracks per chat |
| `PLAYLIST_LIMIT` | `20` | Max playlist tracks expanded per request |
| `AUTO_LEAVE` | `False` | Assistant leaves VC when idle |
| `AUTO_LEAVE_EXCLUDE` | — | Space-separated chat IDs the assistant never auto-leaves |
| `RICH_UI` | `True` | Rich now-playing panel (photo, progress bar, styled buttons); `False` = classic text + inline keyboard. Falls back automatically when the chat disallows photos |
| `AUTO_END` | `False` | End stream when idle timer expires |
| `THUMB_GEN` | `True` | Generate cover thumbnails |
| `VIDEO_PLAY` | `True` | Allow `/vplay` video streams |
| `LANG_CODE` | `en` | Default locale; per-chat override via `/lang` |
| `DEFAULT_THUMB`, `PING_IMG`, `START_IMG` | bundled URLs | Override images |

## Optional (playback fallbacks)

| Var | Description |
|---|---|
| `API_URL`, `API_KEY` | ShrutiBots fallback: `GET {API_URL}/download?url=<id>&type=audio\|video&api_key=` |
| `ONEGRAB_URL`, `ONEGRAB_KEY` | OneGrab: `GET {ONEGRAB_URL}/api/track?url=<watch-url>` + `X-API-Key` → `{cdnurl}` |
| `NEXGEN_AUDIO_URL`, `NEXGEN_VIDEO_URL`, `NEXGEN_KEY` | NexGen: audio `GET {audio}/stream/{id}?api=` streams directly; video `GET {video}/video/{id}?api=` → `{status, link}` |
| `POT_BASE_URL` | `bgutil-ytdlp-pot-provider` server URL; empty disables. v2 binds localhost — expose explicitly for remote use |
| `COOKIES_URL` | Space-separated `batbin.me` URLs (Netscape-format cookies); also supports local `melody/cookies/*.txt` |

> [!WARNING]
> At least one fallback key is strongly recommended on datacenter IPs, where YouTube rate-limits raw yt-dlp.
