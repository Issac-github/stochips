#!/usr/bin/env bash
#
# Run StoChips Docker operations through a temporary proxy on the server host.
# Build proxy settings and runtime proxy settings exist only for this invocation.
#
# Usage:
#   ./scripts/stochips-with-proxy.sh
#   ./scripts/stochips-with-proxy.sh --build-only
#   ./scripts/stochips-with-proxy.sh --login
#   AI_PROVIDER=codex ./scripts/stochips-with-proxy.sh --rebuild --assess-ai 20260710 --force-ai
#
set -euo pipefail

cd "$(cd "$(dirname "$0")/.." && pwd)"

PROXY_URL="${PROXY_URL:-http://127.0.0.1:7892}"
PROXY_CHECK_URL="${PROXY_CHECK_URL:-https://mirrors.ustc.edu.cn/pypi/simple/poetry/}"
START_SERVICES=1
BUILD_IMAGES=1
RUN_CODEX_LOGIN=0
RUNTIME_COMMAND=()
FORCE_AI=0
RECREATE_AGENT=0
BUILD_TARGETS=(stock_agent stock_rpc)
RUNTIME_ACTION=""
BUILD_AND_START_LOGIN=0

usage() {
  cat <<'EOF'
Usage: ./scripts/stochips-with-proxy.sh [options]

Environment variables:
  PROXY_URL        Temporary HTTP proxy URL (default: http://127.0.0.1:7892)
  PROXY_CHECK_URL  URL used to verify the proxy before building

Options:
  (no option)      Build stock_agent and stock_rpc, then start both services
  --build-only     Build stock_agent and stock_rpc without starting services

  --login          Log in to ChatGPT/Codex with the existing stock_agent image
  --assess-ai [date]
                  Generate or reuse the daily Codex market review
  --ai-analyze [date]
                  Compatibility alias for --assess-ai
  --notify-feishu [date]
                  Send the Feishu report through the proxy
  --force-ai       Replace the saved daily review; valid only with --assess-ai
  --rebuild        For --login or a runtime command: rebuild stock_agent and
                   recreate its service container before running the action

Compatibility aliases:
  --codex-login    Equivalent to build/start, then --login
  --login-only     Equivalent to --login
  -h, --help       Show this help
EOF
}

is_date_arg() {
  [[ "${1:-}" =~ ^[0-9]{4}-?[0-9]{2}-?[0-9]{2}$ ]]
}

while [ "$#" -gt 0 ]; do
  arg="$1"
  case "$arg" in
    --build-only)
      START_SERVICES=0
      shift
      ;;
    --codex-login)
      RUN_CODEX_LOGIN=1
      BUILD_AND_START_LOGIN=1
      shift
      ;;
    --login)
      RUN_CODEX_LOGIN=1
      shift
      ;;
    --login-only)
      RUN_CODEX_LOGIN=1
      shift
      ;;
    --assess-ai|--ai-analyze|--notify-feishu)
      if [ -n "$RUNTIME_ACTION" ]; then
        echo "Only one runtime action can be used at a time" >&2
        exit 1
      fi
      case "$arg" in
        --assess-ai)
          RUNTIME_ACTION="assess-ai"
          RUNTIME_COMMAND=(python main.py assess-ai)
          ;;
        --ai-analyze)
          RUNTIME_ACTION="ai-analyze"
          RUNTIME_COMMAND=(python main.py ai-analyze)
          ;;
        --notify-feishu)
          RUNTIME_ACTION="notify-feishu"
          RUNTIME_COMMAND=(python main.py notify-feishu)
          ;;
      esac
      shift
      if [ "$#" -gt 0 ] && is_date_arg "$1"; then
        RUNTIME_COMMAND+=("$1")
        shift
      fi
      ;;
    --force-ai)
      FORCE_AI=1
      shift
      ;;
    --rebuild)
      BUILD_IMAGES=1
      START_SERVICES=0
      RECREATE_AGENT=1
      BUILD_TARGETS=(stock_agent)
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

# One-off commands reuse the current image unless --rebuild is explicit. Resolve
# this after parsing so --rebuild can appear before or after the action.
if [ "$BUILD_AND_START_LOGIN" -eq 0 ] && { [ "$RUN_CODEX_LOGIN" -eq 1 ] || [ -n "$RUNTIME_ACTION" ]; }; then
  START_SERVICES=0
  if [ "$RECREATE_AGENT" -eq 0 ]; then
    BUILD_IMAGES=0
  fi
fi

if [ "$RECREATE_AGENT" -eq 1 ] && [ "$RUN_CODEX_LOGIN" -eq 0 ] && [ -z "$RUNTIME_ACTION" ]; then
  echo "--rebuild must be used with --login or a runtime action" >&2
  exit 1
fi

if [ "$RUN_CODEX_LOGIN" -eq 1 ] && [ -n "$RUNTIME_ACTION" ]; then
  echo "--login cannot be combined with a runtime action" >&2
  exit 1
fi

if [ "$FORCE_AI" -eq 1 ] && [ "$RUNTIME_ACTION" != "assess-ai" ]; then
  echo "--force-ai can only be used with --assess-ai" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed" >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose v2 is not available" >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  echo "Checking temporary proxy: $PROXY_URL"
  curl --fail --silent --show-error \
    --max-time 20 \
    --proxy "$PROXY_URL" \
    --output /dev/null \
    "$PROXY_CHECK_URL"
  echo "Proxy check passed"
else
  echo "Warning: curl is unavailable; skipping the proxy connectivity check" >&2
fi

dotenv_value() {
  local key="$1"
  local default_value="$2"
  local value=""
  if [ -f .env ]; then
    value="$(
      sed -n "s/^[[:space:]]*$key[[:space:]]*=[[:space:]]*//p" .env \
        | tail -n 1 \
        | sed -e 's/[[:space:]]*#.*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
    )"
  fi
  if [ -n "$value" ]; then
    printf '%s' "$value"
  else
    printf '%s' "$default_value"
  fi
}

compose_host_port() {
  local service="$1"
  local private_port="$2"
  local port_line
  port_line="$(docker compose port "$service" "$private_port" 2>/dev/null | head -n 1 || true)"
  if [ -n "$port_line" ]; then
    printf '%s' "${port_line##*:}"
  else
    dotenv_value MYSQL_PORT 3306
  fi
}

stock_agent_image_and_codex_volume() {
  CONTAINER_ID="$(docker compose ps --all -q stock_agent)"
  if [ -z "$CONTAINER_ID" ]; then
    echo "stock_agent container does not exist; build and start it first" >&2
    exit 1
  fi

  IMAGE="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER_ID")"
  CODEX_VOLUME="$(
    docker inspect \
      --format '{{range .Mounts}}{{if eq .Destination "/root/.codex"}}{{.Name}}{{end}}{{end}}' \
      "$CONTAINER_ID"
  )"
  if [ -z "$CODEX_VOLUME" ]; then
    echo "stock_agent does not have a /root/.codex volume" >&2
    exit 1
  fi
}

docker_tty_args() {
  DOCKER_TTY_ARGS=(--interactive)
  if [ -t 0 ] && [ -t 1 ]; then
    DOCKER_TTY_ARGS+=(--tty)
  fi
}

pass_env_if_set() {
  local key="$1"
  local value="${!key:-}"
  if [ -n "$value" ]; then
    RUNTIME_ENV_ARGS+=(--env "$key=$value")
  fi
}

OVERRIDE_FILE=""
cleanup() {
  if [ -n "$OVERRIDE_FILE" ]; then
    rm -f "$OVERRIDE_FILE"
  fi
}
trap cleanup EXIT INT TERM

if [ "$BUILD_IMAGES" -eq 1 ]; then
  OVERRIDE_FILE="$(mktemp "${TMPDIR:-/tmp}/stochips-proxy.XXXXXX")"
  cat >"$OVERRIDE_FILE" <<'EOF'
services:
  stock_agent:
    build:
      network: host
      args:
        HTTP_PROXY: ${STOCHIPS_TEMP_BUILD_PROXY}
        HTTPS_PROXY: ${STOCHIPS_TEMP_BUILD_PROXY}
  stock_rpc:
    build:
      network: host
      args:
        HTTP_PROXY: ${STOCHIPS_TEMP_BUILD_PROXY}
        HTTPS_PROXY: ${STOCHIPS_TEMP_BUILD_PROXY}
EOF

  echo "Building ${BUILD_TARGETS[*]} through the temporary proxy"
  STOCHIPS_TEMP_BUILD_PROXY="$PROXY_URL" \
    docker compose \
      -f docker-compose.yml \
      -f "$OVERRIDE_FILE" \
      build --progress=plain "${BUILD_TARGETS[@]}"
fi

if [ "$RECREATE_AGENT" -eq 1 ]; then
  echo "Recreating stock_agent so the one-off command uses the rebuilt image"
  docker compose up -d --no-deps --force-recreate stock_agent
fi

if [ "$START_SERVICES" -eq 1 ]; then
  echo "Starting stock_agent and stock_rpc"
  docker compose up -d stock_agent stock_rpc
fi

if [ "$RUN_CODEX_LOGIN" -eq 1 ]; then
  stock_agent_image_and_codex_volume
  docker_tty_args

  echo "Starting Codex device-code login through the temporary proxy"
  docker run --rm "${DOCKER_TTY_ARGS[@]}" \
    --network host \
    --env HTTP_PROXY="$PROXY_URL" \
    --env HTTPS_PROXY="$PROXY_URL" \
    --env http_proxy="$PROXY_URL" \
    --env https_proxy="$PROXY_URL" \
    --volume "$CODEX_VOLUME:/root/.codex" \
    "$IMAGE" \
    python main.py codex-login
fi

if [ "${#RUNTIME_COMMAND[@]}" -gt 0 ]; then
  stock_agent_image_and_codex_volume
  docker_tty_args

  if [ "$FORCE_AI" -eq 1 ]; then
    RUNTIME_COMMAND+=(--force-ai)
  fi

  MYSQL_HOST_PORT="$(compose_host_port mysql 3306)"
  MYSQL_USER_VALUE="$(dotenv_value MYSQL_USER stock)"
  MYSQL_PASSWORD_VALUE="$(dotenv_value MYSQL_PASSWORD stock123)"
  DATABASE_URL_VALUE="mysql+pymysql://${MYSQL_USER_VALUE}:${MYSQL_PASSWORD_VALUE}@127.0.0.1:${MYSQL_HOST_PORT}/stock_analysis?charset=utf8mb4"

  ENV_FILE_ARGS=()
  if [ -f .env ]; then
    ENV_FILE_ARGS=(--env-file .env)
  fi

  RUNTIME_ENV_ARGS=()
  pass_env_if_set AI_PROVIDER
  pass_env_if_set AI_FALLBACK_PROVIDER
  pass_env_if_set CODEX_MODEL
  pass_env_if_set CODEX_WORKING_DIRECTORY
  pass_env_if_set DAILY_REVIEW_STRATEGY_PATH

  echo "Running through the temporary proxy: ${RUNTIME_COMMAND[*]}"
  docker run --rm "${DOCKER_TTY_ARGS[@]}" \
    --network host \
    "${ENV_FILE_ARGS[@]+"${ENV_FILE_ARGS[@]}"}" \
    "${RUNTIME_ENV_ARGS[@]+"${RUNTIME_ENV_ARGS[@]}"}" \
    --env DATABASE_URL="$DATABASE_URL_VALUE" \
    --env HTTP_PROXY="$PROXY_URL" \
    --env HTTPS_PROXY="$PROXY_URL" \
    --env http_proxy="$PROXY_URL" \
    --env https_proxy="$PROXY_URL" \
    --env NO_PROXY="localhost,127.0.0.1,mysql,stock_agent,stock_rpc,rag_agent" \
    --env no_proxy="localhost,127.0.0.1,mysql,stock_agent,stock_rpc,rag_agent" \
    --volume "$CODEX_VOLUME:/root/.codex" \
    --volume "$(pwd)/services/agent/logs:/app/logs" \
    "$IMAGE" \
    "${RUNTIME_COMMAND[@]}"
fi

echo "Done; the temporary proxy operation has completed"
