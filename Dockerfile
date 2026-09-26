# syntax=docker/dockerfile:1

# ---- Stage 1: deps — resolve and install Python dependencies with uv ----
FROM python:3.14-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
# --no-install-project: only third-party deps; the app itself is copied later.
# --compile-bytecode: import-time speedup, done once at build not first-run.
# --mount=cache: uv's download cache persists across builds without
# bloating the image layer.
# --python /usr/local/bin/python3.14: pin to the system interpreter. The image
# and .python-version now agree on 3.14, but the pin stays: uv resolves it
# without a managed download.
# UV_PYTHON_DOWNLOADS=never: belt & suspenders — never fetch a managed
# interpreter, always use the image's system python.
# NOTE: the venv records its base prefix, which may resolve as /app/.venv/bin
# under BuildKit (buildx) instead of /usr/local/bin — behavior differs between
# plain `docker build` and buildx, so don't assert on sys.executable here.
# The runtime stage re-validates by importing the real deps instead.
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PYTHON_DOWNLOADS=never \
    uv sync --frozen --no-install-project --compile-bytecode \
        --python /usr/local/bin/python3.14 \
    `# Drop import-time-only weight from the venv before it ships.` \
    && find /app/.venv -name '__pycache__' -type d -prune -exec rm -rf {} + \
    && .venv/bin/python -c 'import sys; print("venv python:", sys.executable)' \
    && .venv/bin/python -c 'import pytgcalls, yt_dlp; print("deps import OK")'

# ---- Stage 2: runtime — only what the bot needs to run ----
FROM python:3.14-slim AS runtime

# Non-root user first so later COPYs can set ownership directly (no chown -R
# rewrite of the ~260MB venv layer at the end).
RUN useradd --system --no-create-home appuser

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
    && FF_NAME=ffmpeg-n9.0-latest-linux64-gpl-9.0 \
    && curl -sL "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/${FF_NAME}.tar.xz" \
        -o "/tmp/${FF_NAME}.tar.xz" \
    && curl -sL https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/checksums.sha256 \
        -o /tmp/ff.sha256 \
    # Verify against the release's own manifest before executing anything from it.
    && (cd /tmp && grep -F "${FF_NAME}.tar.xz" ff.sha256 | sha256sum -c -) \
    && tar -xf "/tmp/${FF_NAME}.tar.xz" -C /tmp \
        "${FF_NAME}/bin/ffmpeg" \
        "${FF_NAME}/bin/ffprobe" \
    && mv "/tmp/${FF_NAME}/bin/ff"* /usr/local/bin/ \
    && ffmpeg -version | head -1 \
    && case "$(dpkg --print-architecture)" in \
        amd64) st_arch=x86_64 ;; \
        arm64) st_arch=aarch64 ;; \
        *) st_arch="" ;; \
       esac \
    && if [ -n "$st_arch" ]; then \
        # Ookla publishes no checksums for these tarballs (checked 2026-09-19);
        # download is TLS-only and failure-tolerant (optional probe).
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
    && rm -rf /var/lib/apt/lists/* "/tmp/${FF_NAME}.tar.xz" "/tmp/${FF_NAME}" /tmp/ff.sha256 /tmp/st.tgz

WORKDIR /app

# venv from the deps stage; uv itself stays behind in stage 1.
COPY --from=deps --chown=appuser:appuser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# App code — last layer so code changes don't invalidate the deps layer.
COPY --chown=appuser:appuser melody ./melody
COPY --chown=appuser:appuser config.py ./

# Runtime state is writable; application files stay owned by appuser.
RUN mkdir -p cache downloads melody/cookies runtime \
    && chown appuser:appuser cache downloads melody/cookies runtime \
    && touch log.txt \
    && chown appuser:appuser log.txt
USER appuser

# start runs `uv run python3 -m melody`; with the venv already on PATH and
# fully synced, uv resolves to it instantly — but uv isn't in this stage.
# Invoke the interpreter directly instead; identical result, no uv needed.
CMD ["/app/.venv/bin/python", "-m", "melody"]
