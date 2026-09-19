# Changelog

All notable changes to Melody. Format based on Keep a Changelog; versions follow semver.

## Unreleased

### Fixed
- Playlist queue listing numbered the first track `0.` instead of `1.` (`queue.add()` returns a 0-based index; display now adds 1).
- Fire-and-forget prefetch task in the playback timer held no strong reference and could be garbage-collected mid-download (asyncio loops keep only weak task refs). Background tasks are now tracked until done.
- Telegram download state (`active_tasks`) leaked on failed downloads; now cleared in `finally`.
- Removed dead condition in the playback progress timer (`timer` is always non-empty).

### Changed
- CI pinned to current action majors; Docker build uses Buildx with GHA cache; added markdown link check (lychee).
- Dockerfile: `COPY --chown` instead of a full `chown -R` layer; venv trimmed (`__pycache__`, `dist-info` removed); corrected the cleanup path for the extracted ffmpeg tree.

### Added
- Queue unit tests locking add/current/next/force_add/clear semantics.
- README with SVG badges, wiki pages, one-click deploy buttons (Heroku/Render/Railway).
