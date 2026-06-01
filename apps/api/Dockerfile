FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Assuming build context is project root to include packages
COPY apps/api/pyproject.toml /usr/src/app/
COPY apps/api/app /usr/src/app/app
COPY packages /usr/src/packages

# Fix for direct pyproject.toml install
RUN pip install --upgrade pip && \
    pip install -e .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
