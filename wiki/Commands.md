# Commands

Legend: **G** = group only, **P** = private, **A** = needs admin/auth, **S** = sudoers, **O** = owner.

## Playback (G)

| Command | Who | Description |
|---|---|---|
| `/play <query\|link>`, reply to audio/video | anyone | Queue audio; searches YouTube if not a link |
| `/vplay <query\|link>` | anyone | Queue as video |
| `/playforce`, `/vplayforce` | A | Skip current and play immediately |
| `/pause` / `/resume` | A | Pause / resume |
| `/skip`, `/next` | A | Skip to next track |
| `/end`, `/stop` | A | Stop and clear |
| `/seek <seconds>`, `/seekback <seconds>` | A | Seek forward/back in current track |
| `/loop [<n>\|off]` | A | Repeat current track 1–10 times; no arg shows status |
| `/shuffle` | A | Shuffle upcoming queue (current keeps playing) |
| `/clear` | A | Drop upcoming queue (current keeps playing) |
| `/queue`, `/playing` | anyone | Show now-playing + queue |
| `/stats` | anyone | Call stats for this chat |

Playlist links are expanded up to `PLAYLIST_LIMIT`, each track capped by `DURATION_LIMIT`, queue capped by `QUEUE_LIMIT`.

## Settings & info

| Command | Scope | Description |
|---|---|---|
| `/start` | anywhere | Start panel; `… start help` shows help |
| `/help` | P | Help panel |
| `/playmode`, `/settings` | G | Toggle direct-play vs inline-search mode |
| `/lang`, `/language` | anywhere | Per-chat language picker (13 locales) |
| `/alive`, `/ping [-s\|speed\|full]` | anywhere | Liveness + latency; `-s` adds Ookla speedtest (`N/A` if binary missing) |

Inline mode: type `@<botusername> <query>` in any chat for YouTube search cards.

## Admin / sudo

| Command | Who | Description |
|---|---|---|
| `/auth`, `/unauth` (reply or username/id) | A | Grant/revoke play access |
| `/authlist` | A | List auth users |
| `/admincache`, `/reload` | A | Refresh admin list |
| `/ac`, `/activevc` | S | Active voice chats |
| `/blacklist`, `/unblacklist`, `/whitelist <id>` | S | Block/unblock chats or users |
| `/broadcast` (reply, flags `-copy -nochat -user`) | S | Forward/copy a message to chats/users |
| `/addsudo`, `/delsudo`, `/rmsudo`, `/listsudo`, `/sudolist` | O/S | Manage sudoers |
| `/logger <on\|off>`, `/logs` | S | Toggle/fetch play logging |
| `/restart` | S | Restart the bot process |
| `/eval`, `/exec` | O | Owner code eval (also on edited messages) |
