FROM python:3.11-slim

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    graphviz \
    graphviz-dev \
    pkg-config \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# pipをアップグレードしてから要件をインストール
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . . 