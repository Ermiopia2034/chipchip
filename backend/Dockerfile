FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Networking resiliency for pip
ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

# Optional mirrors (pass via --build-arg)
ARG PIP_INDEX_URL
ARG PIP_EXTRA_INDEX_URL
RUN if [ -n "$PIP_INDEX_URL" ]; then pip config set global.index-url "$PIP_INDEX_URL"; fi && \
    if [ -n "$PIP_EXTRA_INDEX_URL" ]; then pip config set global.extra-index-url "$PIP_EXTRA_INDEX_URL"; fi

# Python deps
COPY requirements.txt ./
# Upgrade pip tooling first to reduce resolver issues
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# App code
COPY app ./app

EXPOSE 8000

# Simple healthcheck for /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fs http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
