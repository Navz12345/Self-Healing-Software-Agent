FROM python:3.11-slim AS base
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git sqlite3 \
    && rm -rf /var/lib/apt/lists/*
RUN adduser --disabled-password --no-create-home appuser
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS app
COPY app/ /app/
COPY logger.py /app/logger.py
WORKDIR /app
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS orchestrator
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io docker-cli \
    && rm -rf /var/lib/apt/lists/*
COPY . /workspace/
USER appuser
WORKDIR /workspace
