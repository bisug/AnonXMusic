# Melody

<div align="center">
  <img src="https://raw.githubusercontent.com/bisug/Melody/master/.github/melody.jpg" width="480" alt="Melody logo">

  <p>
    <a href="https://github.com/bisug/Melody"><img src="https://img.shields.io/github/stars/bisug/Melody?style=flat-square&logo=github" alt="Stars"></a>
    <a href="https://github.com/bisug/Melody/network/members"><img src="https://img.shields.io/github/forks/bisug/Melody?style=flat-square&logo=github" alt="Forks"></a>
    <a href="https://github.com/bisug/Melody/blob/master/LICENSE"><img src="https://img.shields.io/github/license/bisug/Melody?style=flat-square" alt="License"></a>
    <a href="https://github.com/bisug/Melody/actions/workflows/ci.yml"><img src="https://github.com/bisug/Melody/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/badge/python-3.14%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.14+">
    <img src="https://img.shields.io/badge/version-3.0.3-blueviolet?style=flat-square" alt="Version 3.0.3">
  </p>
</div>

Telegram group voice-chat streaming bot — play audio/video from YouTube (plus Spotify/Apple Music/SoundCloud/m3u8 metadata resolution) directly in Telegram group calls.

Built with [Kurigram](https://github.com/KurimuzonAkuma/kurigram) (Pyrogram fork), [Py-TgCalls](https://github.com/pytgcalls/pytgcalls), `yt-dlp`, and MongoDB.

<p>
  <a href="https://www.python.org/"><img src="https://skillicons.dev/icons?i=python" width="40" height="40" alt="Python"></a>
  <a href="https://www.docker.com/"><img src="https://skillicons.dev/icons?i=docker" width="40" height="40" alt="Docker"></a>
  <a href="https://www.mongodb.com/"><img src="https://skillicons.dev/icons?i=mongodb" width="40" height="40" alt="MongoDB"></a>
  <a href="https://www.heroku.com/"><img src="https://skillicons.dev/icons?i=heroku" width="40" height="40" alt="Heroku"></a>
  <a href="https://github.com/bisug/Melody/actions/workflows/ci.yml"><img src="https://skillicons.dev/icons?i=githubactions" width="40" height="40" alt="GitHub Actions"></a>
  <a href="https://www.linux.org/"><img src="https://skillicons.dev/icons?i=linux" width="40" height="40" alt="Linux"></a>
</p>

- Version: **3.0.3** · Python **3.14+** · License: MIT
- Deploy: VPS / Docker Compose, Render (Docker worker), Heroku (container worker), or local
- Support: [Updates channel](https://t.me/SuMelodyVibes) · [Support group](https://t.me/SuMelodyVibes)

> [!NOTE]
> The bot streams into **group voice/video chats** via assistant (userbot) accounts. It has no inbound HTTP server — it only makes outbound connections to Telegram, MongoDB, and download sources.

## Features

<p>
  <img src="https://img.shields.io/badge/audio-streaming-blue?style=flat-square&logo=telegram&logoColor=white" alt="Audio streaming">
  <img src="https://img.shields.io/badge/video-streaming-blueviolet?style=flat-square&logo=telegram&logoColor=white" alt="Video streaming">
  <img src="https://img.shields.io/badge/youtube-red?style=flat-square&logo=youtube&logoColor=white" alt="YouTube">
  <img src="https://img.shields.io/badge/spotify-green?style=flat-square&logo=spotify&logoColor=white" alt="Spotify">
  <img src="https://img.shields.io/badge/soundcloud-orange?style=flat-square&logo=soundcloud&logoColor=white" alt="SoundCloud">
  <img src="https://img.shields.io/badge/apple_music-black?style=flat-square&logo=applemusic&logoColor=white" alt="Apple Music">
  <img src="https://img.shields.io/badge/mongodb-green?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB">
  <img src="https://img.shields.io/badge/docker-blue?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>


- Audio + video streaming into group voice/video chats via assistant accounts (up to 3 sessions)
- Sources: YouTube search/links/playlists, Spotify/Apple Music/SoundCloud metadata, m3u8, Telegram audio/video replies
- Resilient downloads: `yt-dlp` first, then ShrutiBots → OneGrab → NexGen HTTP fallbacks, plus PO-token provider support
- Queue: shuffle, clear, loop (1–10), seek/seekback, force-play, playlists with duration/queue caps
- Per-chat language (13 locales), auth users, admin cache reload, sudo/blacklist controls, broadcast, stats, inline YouTube search
- Generated thumbnails, play logging to `LOGGER_ID`, auto-leave/auto-end timers

## Quickstart

```bash
git clone https://github.com/bisug/Melody.git && cd Melody
cp sample.env .env   # fill in required values, see Configuration
curl -Ls https://astral.sh/uv/install.sh | sh
uv sync --frozen
uv run python3 -m melody
```

Docker Compose (VPS):

```bash
cp sample.env .env   # fill in values
docker compose up -d --build
docker compose logs -f
```

## Prerequisites

- Python 3.14+, [uv](https://docs.astral.sh/uv/), `ffmpeg` on PATH (Docker image bundles static ffmpeg 9.0 + ffprobe)
- MongoDB URL, Telegram `API_ID`/`API_HASH`, bot token from @BotFather, one Pyrogram v2 string session from @StringFatherBot
- Optional: [Ookla Speedtest CLI](https://www.speedtest.net/apps/cli) — only used by `/ping -s`; without it that field shows `N/A`

## Documentation

Full guides live in [`wiki/`](https://github.com/bisug/Melody/tree/master/wiki):

- [Installation](https://github.com/bisug/Melody/blob/master/wiki/Installation.md) · [Configuration](https://github.com/bisug/Melody/blob/master/wiki/Configuration.md) · [Commands](https://github.com/bisug/Melody/blob/master/wiki/Commands.md) · [Deployment](https://github.com/bisug/Melody/blob/master/wiki/Deployment.md) · [Playback pipeline](https://github.com/bisug/Melody/blob/master/wiki/Playback-Pipeline.md) · [Troubleshooting](https://github.com/bisug/Melody/blob/master/wiki/Troubleshooting.md) · [Development](https://github.com/bisug/Melody/blob/master/wiki/Development.md)

## Usage

1. Add the bot and its assistant(s) to your Telegram group.
2. Promote the bot to admin with invite-users permission and start a voice/video chat.
3. Play: `/play <song>`, video: `/vplay <song>`, then `/pause` `/resume` `/skip` `/queue` `/stop`.
   Full list: [wiki/Commands.md](https://github.com/bisug/Melody/blob/master/wiki/Commands.md).

## Configuration

| Var | Required | Default | Description |
|---|---|---|---|
| `API_ID` `API_HASH` `BOT_TOKEN` `MONGO_URL` `LOGGER_ID` `OWNER_ID` `SESSION` | yes | — | See [wiki/Configuration.md](https://github.com/bisug/Melody/blob/master/wiki/Configuration.md) |
| `SESSION2` `SESSION3` | no | — | Extra assistants |
| `SUPPORT_CHANNEL` `SUPPORT_CHAT` | no | `https://t.me/SuMelodyVibes` | URL / @username / ID |
| `DURATION_LIMIT` (min) `QUEUE_LIMIT` `PLAYLIST_LIMIT` | no | `60` `20` `20` | Playback caps |
| `AUTO_LEAVE` `AUTO_END` `THUMB_GEN` `VIDEO_PLAY` | no | `False` `False` `True` `True` | Behaviour toggles |
| `LANG_CODE` | no | `en` | Default locale (13 available, per-chat `/lang`) |
| `API_URL`+`API_KEY` / `ONEGRAB_*` / `NEXGEN_*` | no | — | Download fallbacks (strongly recommended on VPS) |
| `POT_BASE_URL` | no | — | PO-token provider for yt-dlp |
| `COOKIES_URL` | no | — | Space-separated batbin.me Netscape-cookie URLs |
| `DEFAULT_THUMB` `PING_IMG` `START_IMG` | no | bundled URLs | Image overrides |

> [!TIP]
> `config.py` is the source of truth; `sample.env` shows the deploy-time shape.

## Deployment

<p>
  <a href="https://dashboard.heroku.com/new?template=https://github.com/bisug/Melody.git"><img src="https://img.shields.io/badge/Deploy%20On%20Heroku-430098?style=for-the-badge&logo=heroku&logoColor=white" alt="Deploy on Heroku"></a>
  <a href="https://render.com/deploy?repo=https://github.com/bisug/Melody.git"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="28"></a>
  <a href="https://railway.com/deploy?repo=https://github.com/bisug/Melody"><img src="https://railway.com/button.svg" alt="Deploy on Railway" height="32"></a>
</p>

- **Docker Compose (VPS):** `cp sample.env .env`, `docker compose up -d --build`. Details: [wiki/Deployment.md](https://github.com/bisug/Melody/blob/master/wiki/Deployment.md).
- **Render:** Blueprint worker (`render.yaml`, manual deploys, paid instance).
- **Heroku:** container-stack worker (`heroku.yml` + `app.json`), scale `worker=1`.
- **Railway:** one-click deploy above (Dockerfile auto-detected); set required env vars when prompted.
- **Assisted VPS setup:** run `./setup` (Debian/Ubuntu).

## Support

<p>
  <a href="https://t.me/SuMelodyVibes"><img src="https://img.shields.io/badge/updates_channel-229ED9?style=flat-square&logo=telegram&logoColor=white" alt="Updates channel"></a>
  <a href="https://t.me/SuMelodyVibes"><img src="https://img.shields.io/badge/support_group-229ED9?style=flat-square&logo=telegram&logoColor=white" alt="Support group"></a>
  <a href="https://github.com/bisug/Melody/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"></a>
</p>


- Updates: https://t.me/SuMelodyVibes · Support: https://t.me/SuMelodyVibes
- License: MIT — see [LICENSE](https://github.com/bisug/Melody/blob/master/LICENSE).
