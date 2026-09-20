# Development

- Layout: `melody/__main__.py` (boot/idle/shutdown) · `melody/core/` (bot, calls, mongo, youtube, providers, telegram, userbot) · `melody/plugins/` (auto-loaded via `all_modules`) · `melody/helpers/` (queue, thumbnails, inline, utils) · `melody/locales/*.json` (13 languages) · `config.py`. (Unit tests live outside the repo — see `.gitignore`.)
- Requires Python 3.14, `uv` with `uv.lock --frozen`. Docker uses a two-stage build (deps → runtime with static ffmpeg 9.0 + optional Ookla CLI, non-root `appuser`).
- Checks: `uv run ruff check . --select=E9,F63,F7,F82` (also CI: `.github/workflows/ci.yml` + docker build). Unit tests, if present locally, run via `uv run python -m unittest discover -s tests -v`.
- Plugins: add a file under `melody/plugins/` — picked up automatically. Guard group commands with `~app.bl_users`; admin ones with `@admin_check`/`@can_manage_vc`; owner/sudo via `app.owner`/`app.sudoers`.
- Locales: translate `melody/locales/en.json` keys; keep key names stable; send to @SuMelodyVibes or open a PR.
