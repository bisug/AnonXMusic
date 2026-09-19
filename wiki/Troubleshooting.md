# Troubleshooting

## “Confirm you're not a bot” / empty downloads on VPS

Datacenter IPs trigger YouTube checks. Fix in order: 1. set `POT_BASE_URL` to a reachable provider, 2. add `COOKIES_URL` (batbin.me, Netscape format, space-separated for multiples), 3. configure `API_KEY`/`ONEGRAB_KEY`/`NEXGEN_KEY` fallbacks.

## Cookies

- Remote: upload Netscape cookies to batbin.me, put URL(s) in `COOKIES_URL`.
- Local: drop `*.txt` (Netscape format) in `melody/cookies/` (persisted as a volume in compose).

## `/ping -s` shows N/A

Ookla binary missing or unsupported arch, or the 90 s probe timed out. Install via `./setup` or the Dockerfile step; plain `/ping` still works.

## Bot joins but no audio

Assistant account must join the VC: promote the bot with invite-users permission, start a voice chat first, check `/activevc`, ensure `VIDEO_PLAY`/`DURATION_LIMIT` aren't blocking, and confirm the log group (`LOGGER_ID`) is reachable.

## Render/Heroku won't start

Render: paid worker required; trigger deploys manually (`autoDeployTrigger: off`). Heroku: scale `worker=1`; container stack only — buildpack stacks ignore `heroku.yml`.
