FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      libmagic1 \
      libpq-dev \
      poppler-utils \
      tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 translatrix
WORKDIR /app

COPY requirements-runtime.txt ./
RUN pip install --upgrade pip && pip install -r requirements-runtime.txt

COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x /app/docker-entrypoint.sh \
    && mkdir -p /app/data/uploads \
    && chown -R translatrix:translatrix /app

USER translatrix
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=5 \
  CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
