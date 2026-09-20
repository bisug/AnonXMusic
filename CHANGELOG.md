# Changelog

All notable changes to Melody. Format based on Keep a Changelog; versions follow semver.

## Unreleased

### Fixed
- Playlist queue listing numbered the first track `0.` instead of `1.` (`queue.add()` returns a 0-based index; display now adds 1).
- Fire-and-forget prefetch task in the playback timer held no strong reference and could be garbage-collected mid-download (asyncio loops keep only weak task refs). Background tasks are now tracked until done.
- Telegram download state (`active_tasks`) leaked on failed downloads; now cleared in `finally`.
- Removed dead condition in the playback progress timer (`timer` is always non-empty).
- `/play` on a replied Telegram file crashed with `AttributeError: 'Media' object has no attribute 'is_live'`; `Media` now carries the flag like `Track`.
- `Language` now merges English under every locale, so a missing translation key can no longer `KeyError` a handler (`/shuffle`, `/clear` failed in every non-English locale).
- The download cache no longer accepts yt-dlp `.part`/`.ytdl` artifacts as finished files, which could play a truncated track during a concurrent download.
- A concurrent Telegram download cleared the in-flight guard on early return, allowing a duplicate download to the same `.temp` path and corrupting it.
- Unvalidated language callback data could persist an unknown code and brick a chat's language lookups; unknown codes are now rejected.
- `setup` writes `.env` with `0600` (it holds the bot token and string session).

### Changed
- CI pinned to current action majors; Docker build uses Buildx with GHA cache; added markdown link check (lychee).
- Dockerfile: `COPY --chown` instead of a full `chown -R` layer; venv trimmed (`__pycache__`, `dist-info` removed); corrected the cleanup path for the extracted ffmpeg tree.
- Audit cleanup: plugin modules load in a deterministic (sorted) order; `get_languages()` reuses the locales loaded at startup instead of re-globbing the directory; the three HTTP download providers share one `.part` cleanup helper.
- Removed dead code (`MessageIdInvalid` import, unused `api_warned` flag, empty `Utilities.__init__`, one-line `idle()` wrapper) and hoisted `plugins/queue.py`'s function-local `random` import to module scope.

### Added

- Autoplay (`/autoplay [on|off]`, settings toggle): when the queue ends, a random related track keeps playing; related search excludes the current track, live entries and over-limit tracks.
- Channel play (`/channelplay [on|off]`): audio posted in the group's linked channel is queued/played automatically; assistant-join logic extracted into a shared `join_assistant()`.
- Rich now-playing UI (kurigram rich messages): photo, title, progress-bar row and styled Pause/Resume · Replay · Skip · Stop controls, reusing the existing `controls` callbacks; timer re-renders progress; automatic fallback to the classic text + inline-keyboard UI; `RICH_UI` env toggle.
- `/settings` gained an Autoplay row; wiki architecture page + SVG diagram; credits section in the README.
- Queue unit tests locking add/current/next/force_add/clear semantics.
- README with SVG badges, wiki pages, one-click deploy buttons (Heroku/Render/Railway).
