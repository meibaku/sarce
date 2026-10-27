FROM python:3.12-slim-bookworm

ARG STOCKFISH_DOWNLOAD_URL
ARG STOCKFISH_SHA256

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

ENV STOCKFISH_PATH=/usr/local/bin/stockfish \
    PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl --fail http://127.0.0.1:8000/health/ready || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
