# Build the Go gRPC gateway.
FROM golang:1.23 AS go-builder

WORKDIR /src/stock-rpc
COPY services/stock-rpc/go.mod services/stock-rpc/go.sum ./
RUN go mod download
COPY services/stock-rpc/ ./
RUN go build -o /out/stock-rpc ./cmd/stock-rpc

# Runtime keeps the existing Python agent code and dependencies.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    TZ=Asia/Shanghai \
    STOCK_RPC_ADDR=:50051 \
    STOCK_RPC_AGENT_DIR=/app \
    PYTHON_BIN=python

ARG DEBIAN_MIRROR=https://mirrors.aliyun.com/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.aliyun.com/debian-security
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com

ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g; s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY services/agent/pyproject.toml services/agent/poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --without dev

COPY services/agent/ ./
COPY --from=go-builder /out/stock-rpc /usr/local/bin/stock-rpc

RUN mkdir -p logs && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

EXPOSE 50051

CMD ["stock-rpc"]
