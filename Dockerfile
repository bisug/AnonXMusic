# syntax=docker/dockerfile:1

# ---- Stage 1: deps — resolve and install Python dependencies with uv ----
FROM python:3.14-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
# --no-install-project: only third-party deps; the app itself is copied later.
# --compile-bytecode: import-time speedup, done once at build not first-run.
# --mount=cache: uv's download cache persists across builds without
# bloating the image layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --compile-bytecode

# ---- Stage 2: runtime — only what the bot needs to run ----
FROM python:3.14-slim AS runtime

# Static ffmpeg 9.0 (BtbN GPL build) — newer than any Debian release ships,
# so the reconnect_max_retries / reconnect_delay_total_max input flags in
# anony/core/calls.py are honored. pytgcalls strips unknown flags on older
# builds, so the app stays compatible either way. Only ffmpeg + ffprobe are
# extracted (ffplay alone is ~145MB and needs X libs the bot never uses).
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && curl -sL https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz \
        -o /tmp/ff.tar.xz \
    && tar -xf /tmp/ff.tar.xz -C /tmp \
        ffmpeg-n9.0-latest-linux64-gpl-9.0/bin/ffmpeg \
        ffmpeg-n9.0-latest-linux64-gpl-9.0/bin/ffprobe \
    && mv /tmp/ffmpeg-n9.0-latest-linux64-gpl-9.0/bin/ff* /usr/local/bin/ \
    && ffmpeg -version | head -1 \
    # Drop the fetch tools — the runtime never needs them.
    && apt-get purge -y curl xz-utils \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/ff.tar.xz /tmp/ffmpeg-n9.0-latest-linux64-gpl-9.0

WORKDIR /app

# venv from the deps stage; uv itself stays behind in stage 1.
COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# App code — last layer so code changes don't invalidate the deps layer.
COPY anony ./anony
COPY config.py ./

# Run as a non-root user; the bot only talks outbound to Telegram/Mongo.
RUN useradd --system --no-create-home appuser \
    && mkdir -p cache downloads anony/cookies \
    && chown -R appuser:appuser /app
USER appuser

# start runs `uv run python3 -m anony`; with the venv already on PATH and
# fully synced, uv resolves to it instantly — but uv isn't in this stage.
# Invoke the interpreter directly instead; identical result, no uv needed.
CMD ["/app/.venv/bin/python", "-m", "anony"]
