FROM python:3.12-slim AS builder

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.12-slim AS backend

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/usr/local/bin:$PATH
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY ./app_backend ./app_backend
COPY ./shared ./shared
COPY ./config ./config

EXPOSE 8000

FROM node:20-alpine AS frontend-builder

WORKDIR /fe

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --legacy-peer-deps 2>/dev/null || npm ci --legacy-peer-deps

COPY frontend/ ./
RUN npm run build

FROM backend AS server

COPY --from=frontend-builder /fe/dist ./app_backend/static

CMD ["uvicorn", "app_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
