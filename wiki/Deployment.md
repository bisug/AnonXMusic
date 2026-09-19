# Deployment

<p>
  <a href="https://dashboard.heroku.com/new?template=https://github.com/bisug/Melody.git"><img src="https://img.shields.io/badge/Deploy%20On%20Heroku-430098?style=for-the-badge&logo=heroku&logoColor=white" alt="Deploy on Heroku"></a>
  <a href="https://render.com/deploy?repo=https://github.com/bisug/Melody.git"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="28"></a>
  <a href="https://railway.com/deploy?repo=https://github.com/bisug/Melody"><img src="https://railway.com/button.svg" alt="Deploy on Railway" height="32"></a>
</p>

> [!NOTE]
> Railway has no `railway.json`/`railway.toml` in this repo yet — it will auto-detect the `Dockerfile`. Fill the required env vars in the Railway dashboard after clicking deploy.

## Render (Blueprint)

Repo ships `render.yaml`: Docker background **worker**, Singapore region, `autoDeployTrigger: off`.

1. Fork the repo. 2. Render Dashboard → Blueprints → connect fork/branch with `render.yaml`. 3. Fill required vars (`API_ID API_HASH BOT_TOKEN MONGO_URL LOGGER_ID OWNER_ID SESSION`), optional `SUPPORT_* API_URL API_KEY COOKIES_URL`. 4. Deploy manually after pushes.

Background workers need a paid instance; no build/start command needed (Dockerfile `CMD` runs the bot).

## Heroku (container stack)

Ships `heroku.yml` + `app.json` + `Procfile` (`worker: python3 -m melody`). Runs as a `worker` dyno; `app.json` provisions one `basic` worker.

```bash
heroku ps:scale worker=1 -a <your-app>
```

No free tier — a paid `basic`+ dyno is required. On buildpack stacks `heroku.yml` is ignored and `Procfile` runs instead.

## Railway (one-click)

Click **Deploy on Railway** above, then set the required vars (`API_ID API_HASH BOT_TOKEN MONGO_URL LOGGER_ID OWNER_ID SESSION`) plus any optional fallbacks. Railway auto-detects the `Dockerfile`; no port config needed (the bot makes outbound connections only).

## VPS / Docker

Use `docker-compose.yml` (`anonxmusic` + optional `pot-provider`, restart `unless-stopped`, no published ports, `./melody/cookies` persisted). Set `POT_BASE_URL=http://pot-provider:4416` to enable PO tokens.
