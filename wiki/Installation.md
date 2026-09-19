# Installation

## Local / VPS (uv)

```bash
git clone https://github.com/bisug/Melody.git && cd Melody
cp sample.env .env   # fill in required values
curl -Ls https://astral.sh/uv/install.sh | sh
uv sync --frozen
uv run python3 -m melody
```

Windows (PowerShell): `irm https://astral.sh/uv/install.ps1 | iex`, then the same `uv sync` / `uv run` commands.

## Assisted setup (Debian/Ubuntu)

`./setup` updates apt, installs python3/ffmpeg/curl/unzip, installs `uv`, installs deps via `uv sync --frozen`, installs the optional Ookla Speedtest CLI, then prompts for `API_ID API_HASH BOT_TOKEN MONGO_URL LOGGER_ID SESSION OWNER_ID` and writes `.env`.

## Docker Compose (recommended for VPS)

```bash
cp sample.env .env
docker compose up -d --build
docker compose logs -f
docker compose down   # stop
```

Includes an optional `pot-provider` service (`brainicism/bgutil-ytdlp-pot-provider`); set `POT_BASE_URL=http://pot-provider:4416` to route yt-dlp PO-token requests through it.
