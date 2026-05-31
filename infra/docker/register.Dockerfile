FROM python:3.12-slim

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY shared ./shared
COPY src/register ./src/register

EXPOSE 8100

CMD ["uvicorn", "src.register.main:app", "--host", "0.0.0.0", "--port", "8100"]