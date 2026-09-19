# syntax=docker/dockerfile:1

# ---- Stage 1: deps — resolve and install Python dependencies with uv ----
FROM python:3.14-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
# --no-install-project: only third-party deps; the app itself is copied later.
# --compile-bytecode: import-time speedup, done once at build not first-run.
# --mount=cache: uv's download cache persists across builds without
# bloating the image layer.
# --python /usr/local/bin/python3.14: pin to the system interpreter. The image
# and .python-version now agree on 3.14, but the pin stays: uv resolves it
# without a managed download, and the venv keeps pointing at a path that also
# exists in the runtime stage (which only copies /app/.venv).
# UV_PYTHON_DOWNLOADS=never: belt & suspenders — never fetch a managed
# interpreter, always use the image's system python.
# Sanity check: the venv python must resolve INSIDE this stage, and the
# symlink target must exist in the runtime stage too (same base image).
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PYTHON_DOWNLOADS=never \
    uv sync --frozen --no-install-project --compile-bytecode \
        --python /usr/local/bin/python3.14 \
    && .venv/bin/python -c 'import sys; assert sys.executable.startswith("/usr/local/bin/python3.14"), sys.executable; print("venv python:", sys.executable)' \
    && .venv/bin/python -c 'import pytgcalls, yt_dlp; print("deps import OK")'

# ---- Stage 2: runtime — only what the bot needs to run ----
FROM python:3.14-slim AS runtime

# Static ffmpeg 9.0 (BtbN GPL build) — newer than any Debian release ships,
# so the reconnect_max_retries / reconnect_delay_total_max input flags in
# melody/core/calls.py are honored. pytgcalls strips unknown flags on older
# builds, so the app stays compatible either way. Only ffmpeg + ffprobe are
# extracted (ffplay alone is ~145MB and needs X libs the bot never uses).
#
# Ookla Speedtest CLI 1.2.0 (the latest release; the official Go binary, not
# the abandoned speedtest-cli PyPI package) powers "/ping speed". Optional:
# /ping degrades to "N/A" when the binary is absent or the arch is unsupported.
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && curl -sL https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz \
        -o /tmp/ff.tar.xz \
    && tar -xf /tmp/ff.tar.xz -C /tmp \
        ffmpeg-n9.0-latest-linux64-gpl-9.0/bin/ffmpeg \
        ffmpeg-n9.0-latest-linux64-gpl-9.0/bin/ffprobe \
    && mv /tmp/ffmpeg-n9.0-latest-linux64-gpl-9.0/bin/ff* /usr/local/bin/ \
    && ffmpeg -version | head -1 \
    && case "$(dpkg --print-architecture)" in \
        amd64) st_arch=x86_64 ;; \
        arm64) st_arch=aarch64 ;; \
        *) st_arch="" ;; \
       esac \
    && if [ -n "$st_arch" ]; then \
        curl -sL "https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-${st_arch}.tgz" \
            -o /tmp/st.tgz \
        && tar -xzf /tmp/st.tgz -C /tmp speedtest \
        && mv /tmp/speedtest /usr/local/bin/speedtest \
        && chmod +x /usr/local/bin/speedtest \
        && speedtest --version; \
       else \
        echo "No Ookla Speedtest build for $(dpkg --print-architecture); /ping speed will report N/A"; \
       fi \
    # Drop the fetch tools — the runtime never needs them.
    && apt-get purge -y curl xz-utils \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/ff.tar.xz /tmp/st.tgz /tmp/ffmpeg-n9.0-latest-linux64-gpl-9.0

WORKDIR /app

# venv from the deps stage; uv itself stays behind in stage 1.
COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# App code — last layer so code changes don't invalidate the deps layer.
COPY melody ./melody
COPY config.py ./

# Run as a non-root user; the bot only talks outbound to Telegram/Mongo.
RUN useradd --system --no-create-home appuser \
    && mkdir -p cache downloads melody/cookies \
    && chown -R appuser:appuser /app
USER appuser

# start runs `uv run python3 -m melody`; with the venv already on PATH and
# fully synced, uv resolves to it instantly — but uv isn't in this stage.
# Invoke the interpreter directly instead; identical result, no uv needed.
CMD ["/app/.venv/bin/python", "-m", "melody"]
