FROM python:3.12-slim-bookworm AS builder

ARG STOCKFISH_DOWNLOAD_URL=https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-linux-x86-64-universal.tar.gz
ARG STOCKFISH_SHA256=9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f
ARG PILOT_ARTIFACT_SHA

RUN test -n "$STOCKFISH_DOWNLOAD_URL" && test -n "$STOCKFISH_SHA256" \
    && apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && curl --fail --location "$STOCKFISH_DOWNLOAD_URL" -o /tmp/stockfish.tar \
    && echo "$STOCKFISH_SHA256  /tmp/stockfish.tar" | sha256sum --check - \
    && mkdir -p /opt/stockfish \
    && tar -xf /tmp/stockfish.tar -C /opt/stockfish --strip-components=1 \
    && install "$(find /opt/stockfish -type f -name 'stockfish*' -perm /111 | head -n 1)" /usr/local/bin/stockfish \
    && rm -rf /tmp/stockfish.tar /opt/stockfish

WORKDIR /app
COPY requirements.txt requirements-maia.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-maia.txt
COPY app ./app
COPY scripts ./scripts

ENV STOCKFISH_PATH=/usr/local/bin/stockfish \
    HUMAN_MODEL=maia2 \
    MAIA2_CACHE_DIR=/opt/sarce/maia2 \
    PILOT_EXPECTED_STOCKFISH_VERSION=19 \
    PILOT_EXPECTED_MAIA_VERSION=0.11.0
RUN test -n "$PILOT_ARTIFACT_SHA" \
    && python scripts/pilot_runtime_check.py --artifact-sha "$PILOT_ARTIFACT_SHA" \
      --verified-by image-build --output /opt/sarce/runtime-manifest.json

FROM python:3.12-slim-bookworm AS runtime
ARG PILOT_ARTIFACT_SHA
ARG BUILD_TIME
ARG SOURCE_REVISION
LABEL org.opencontainers.image.revision=$PILOT_ARTIFACT_SHA \
      org.opencontainers.image.created=$BUILD_TIME \
      org.opencontainers.image.source=$SOURCE_REVISION

WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY --from=builder /opt/sarce /opt/sarce
COPY --from=builder /app/app ./app
COPY --from=builder /app/scripts ./scripts

ENV STOCKFISH_PATH=/usr/local/bin/stockfish \
    HUMAN_MODEL=maia2 \
    MAIA2_CACHE_DIR=/opt/sarce/maia2 \
    PILOT_ARTIFACT_SHA=$PILOT_ARTIFACT_SHA \
    PILOT_RUNTIME_MANIFEST_PATH=/opt/sarce/runtime-manifest.json \
    PILOT_EXPECTED_STOCKFISH_VERSION=19 \
    PILOT_EXPECTED_MAIA_VERSION=0.11.0 \
    POSITION_EVALS_ENABLED=false \
    PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=4)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
