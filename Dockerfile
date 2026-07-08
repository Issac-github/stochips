# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS python-runtime-base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    TZ=Asia/Shanghai

ARG DEBIAN_MIRROR=https://mirrors.aliyun.com/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.aliyun.com/debian-security
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com

ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    POETRY_REQUESTS_TIMEOUT=120

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g; s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    tzdata

COPY services/agent/pyproject.toml services/agent/poetry.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pypoetry \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry config installer.max-workers 1 && \
    poetry install --no-interaction --no-ansi --without dev

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


FROM python-runtime-base AS stock_agent

COPY services/agent/ ./
RUN mkdir -p logs

CMD ["python", "main.py", "schedule"]


FROM golang:1.23 AS stock_rpc_go_builder

WORKDIR /src/stock-rpc
ARG GOPROXY=https://goproxy.cn,direct
ENV GOPROXY=${GOPROXY}

COPY services/stock-rpc/go.mod services/stock-rpc/go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
COPY services/stock-rpc/ ./
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go build -o /out/stock-rpc ./cmd/stock-rpc


FROM python-runtime-base AS stock_rpc

ENV STOCK_RPC_ADDR=:50051 \
    STOCK_RPC_AGENT_DIR=/app \
    PYTHON_BIN=python

COPY services/agent/ ./
COPY --from=stock_rpc_go_builder /out/stock-rpc /usr/local/bin/stock-rpc
RUN mkdir -p logs

EXPOSE 50051

CMD ["stock-rpc"]
