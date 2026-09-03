<div align="center">

<h2>AnonXMusic</h2>

<b>Telegram Group Calls Streaming Bot</b><br>
Supports YouTube, Spotify, Resso, Apple Music, SoundCloud and M3U8 links.

<a href="https://github.com/bisug/AnonXMusic/stargazers">
    <img src="https://img.shields.io/github/stars/bisug/AnonXMusic?color=blueviolet&logo=github&logoColor=black&style=for-the-badge" alt="Stars"/>
</a>
<a href="https://github.com/bisug/AnonXMusic/network/members">
    <img src="https://img.shields.io/github/forks/bisug/AnonXMusic?color=blueviolet&logo=github&logoColor=black&style=for-the-badge" alt="Forks"/>
</a>
<a href="https://github.com/bisug/AnonXMusic/blob/master/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License"/>
</a>
<a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Written%20in-Python-blue?style=for-the-badge&logo=python" alt="Python"/>
</a>
<br>

<img src="https://github.com/bisug/AnonXMusic/blob/master/.github/anonx.jpg" width="720" height="auto">

AnonXMusic lets you stream high-quality and low-latency audio and video playback into telegram group video chats.<br>
Built with Python, Pyrogram, and Py-TgCalls, it’s optimized for reliability and easy deployment on Heroku, Render, VPS, or Docker.
</div>

<hr>

<h2>🔥 Features</h2>

- 🎧 Stream low-latency audio in real time to <b>Telegram group video chats</b>
- 🌐 Supports multiple platforms like <b>YouTube, Spotify, Apple Music, SoundCloud</b>
- ⚡ Advanced queue management with auto-play
- ⚙️ Easy deployment — works on Local, VPS, Heroku, or Render
- ❤️ Built with Python
<hr>

<h2>☁️ Manual Deployment</h2>

<h3>✔️ Prerequisites</h3>

- <a href="https://www.python.org">Python 3.13+</a> installed  
- <a href="https://deno.com/">deno</a> & <a href="https://ffmpeg.org/">ffmpeg</a> installed on your system  
- Required variables mentioned in <a href="https://github.com/bisug/AnonXMusic/blob/master/sample.env">sample.env</a>

<details>
    <summary>
        <h3>Local / VPS Setup</h3>
    </summary>


<h4>🐧 Linux/macOS</h4>

```bash
git clone https://github.com/bisug/AnonXMusic.git && cd AnonXMusic

# Install uv
curl -Ls https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install dependencies
uv sync --frozen

# Rename and configure environment variables
mv sample.env .env
# Edit .env with your credentials

# Start the bot
uv run python3 -m anony
```

<h4>🪟 Windows (PowerShell)</h4>

```bash
git clone https://github.com/bisug/AnonXMusic.git && cd AnonXMusic

# Install uv
irm https://astral.sh/uv/install.ps1 | iex

# Install dependencies
uv sync --frozen

# Rename and configure environment variables
mv sample.env .env
# Edit .env with your credentials

# Start the bot
uv run python3 -m anony

> ⭐ Same command works everywhere — Linux, macOS, Windows, Git Bash, WSL.
```

<h4>🐳 VPS with Docker Compose</h4>

The included <code>docker-compose.yml</code> is the easiest way to run the bot on a VPS with automatic restarts.

```bash
git clone https://github.com/bisug/AnonXMusic.git && cd AnonXMusic

# Configure environment variables
cp sample.env .env
# Edit .env with your credentials

# Build and start in the background
docker compose up -d --build

# Follow logs
docker compose logs -f

# Stop the bot
docker compose down
```

</details>

<details>
    <summary>
        <h3>Deploy to Render</h3>
    </summary>

> Click on the button below to deploy on Render<br>
    <a href="https://render.com/deploy?repo=https://github.com/bisug/AnonXMusic.git">
        <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render"/>
    </a>

This repository includes a <code>render.yaml</code> Blueprint for Render. It deploys AnonXMusic as a Docker background worker because the bot runs continuously and does not expose an HTTP server.

To deploy from your fork instead:

1. Fork this repository.
2. Open the <a href="https://dashboard.render.com/blueprints/new">Render Blueprint dashboard</a>.
3. Connect your fork and select the branch that contains <code>render.yaml</code>.
4. Fill in the required environment variables:

```env
API_ID=
API_HASH=
BOT_TOKEN=
MONGO_URL=
LOGGER_ID=
OWNER_ID=
SESSION=
```

Optional:

```env
COOKIES_URL=
```

Use <code>COOKIES_URL</code> only if your deployment needs cookies for YouTube playback. It accepts one or more <code>batbin.me</code> URLs separated by spaces.

5. Deploy the Blueprint.

> Auto deploy is disabled in <code>render.yaml</code>. Trigger deploys manually from Render after pushing updates.
> Render background workers require a paid worker instance. Use the Dockerfile included in this repo; no separate build or start command is needed.
</details>

<details>
    <summary>
        <h3>Deploy to Heroku</h3>
    </summary>

> Click on the button below to deploy on Heroku<br>
    <a href="https://dashboard.heroku.com/new?template=https://github.com/bisug/AnonXMusic.git">
        <img src="https://img.shields.io/badge/Deploy%20On%20Heroku-black?style=for-the-badge&logo=heroku"/>
    </a>

This repo ships a container-stack <code>heroku.yml</code> and <code>app.json</code>. The bot runs as a <code>worker</code> dyno (no web process), and <code>app.json</code> provisions one <code>basic</code> worker automatically on deploy.

> Heroku has no free tier — a paid <code>basic</code> (or higher) worker dyno is required. If the bot doesn't start, ensure the worker is scaled: `heroku ps:scale worker=1 -a <your-app>`.
</details>

<hr>

<h2>⚙️ Configuration</h2>

Edit <code>.env</code> (or set variables in your hosting environment):
<details>
    <summary>Here's an example of the .env file</summary>

```env
API_ID=123456
API_HASH=abcdef1234567890
BOT_TOKEN=123456:ABC-DEF
OWNER_ID=123456789
LOGGER_ID=-1001234567890
MONGO_URL=mongodb+srv://
SESSION=BQgfh...AA
```

> 📝 Check <a href="https://github.com/bisug/AnonXMusic/blob/master/config.py">config.py</a> for all available options.
</details>

<hr>

<h2>🧐 Usage</h2>

1. Add the bot to your Telegram group.  
2. Promote it to <b>admin</b> with invite users permission.  
3. Use commands in the chat to control playback:
<details>
    <summary>Commands overview</summary>
    <pre>
/play [song name or link] -> Play audio in the videochat
/vplay [song name or link] -> Play video in the videochat
/pause -> Pause playback
/resume -> Resume playback
/skip -> Skip to next track
/stop -> Stop playback
/seek -> Seeks the stream
/queue -> Show queue
    </pre>
</details>

<hr>

<h2>❤️ Contributing</h2>

Contributions are welcome!

1. Fork the repository.  
2. Create your branch: <code>git checkout -b feature/new</code>.  
4. Commit changes: <code>git commit -m 'New feature'</code>.  
5. Push: <code>git push origin feature/new</code>
6. Open a Pull Request.

<hr>

<h2>🗒️ License</h2>

This project is licensed under the <b>MIT License</b> — see <a href="https://github.com/bisug/AnonXMusic/blob/master/LICENSE">LICENSE</a> for details.

<hr>

<h2>🤞 Updates and support</h2>

- <a href="https://t.me/SuMelodyVibes">Updates channel</a>
- <a href="https://t.me/SuMelodyVibes">Support group</a>

<hr>

<h2>👀 Acknowledgements</h2>

- Inspired by other open-source Telegram music bots.
- Thanks to all the <a href="https://github.com/bisug/AnonXMusic/graphs/contributors">contributors</a>.

<hr>

<div align="center">

⭐ Enjoying the tunes? <b>Star the repo</b> — feedback keeps the rhythm going!

</div>
