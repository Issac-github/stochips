#!/usr/bin/env bash
#
# 一键部署脚本：在仓库根目录编排 mysql + stock_agent + stock_rpc。
# 用法：
#   ./deploy.sh            正常部署（保留已有数据）
#   ./deploy.sh --fresh    先清空旧数据卷再部署
#   ./deploy.sh --no-build 不重新构建镜像，直接 up
#   ./deploy.sh -h         查看帮助
#
set -euo pipefail

# 切换到脚本所在目录（仓库根目录），不依赖调用方 CWD。macOS 缺少 readlink -f，
# 这里用可移植写法。
cd "$(cd "$(dirname "$0")" && pwd)"

# ---- 日志辅助 ----
if [ -t 1 ]; then
  C_RESET='\033[0m'; C_INFO='\033[0;34m'; C_OK='\033[0;32m'
  C_WARN='\033[0;33m'; C_ERR='\033[0;31m'
else
  C_RESET=''; C_INFO=''; C_OK=''; C_WARN=''; C_ERR=''
fi
log()  { printf '%b[deploy]%b %s\n' "$C_INFO" "$C_RESET" "$*"; }
ok()   { printf '%b[ ok  ]%b %s\n' "$C_OK"   "$C_RESET" "$*"; }
warn() { printf '%b[warn ]%b %s\n' "$C_WARN" "$C_RESET" "$*" >&2; }
err()  { printf '%b[error]%b %s\n' "$C_ERR"  "$C_RESET" "$*" >&2; }

usage() {
  cat <<'EOF'
用法: ./deploy.sh [选项]

选项:
  --fresh      部署前执行 docker compose down -v，删除旧的 mysql 数据卷
  --no-build   跳过镜像构建，直接 docker compose up -d
  -h, --help   显示本帮助

部署流程:
  1. 预检 docker / docker compose
  2. 校验 .env（缺失则从 .env.example 生成并退出，提示填写密钥）
  3. docker compose up（默认 --build）
  4. 轮询等待 mysql 与 stock_rpc 健康，超时退出非零
EOF
}

# ---- 解析参数 ----
FRESH=0
BUILD=1
for arg in "$@"; do
  case "$arg" in
    --fresh)    FRESH=1 ;;
    --no-build) BUILD=0 ;;
    -h|--help)  usage; exit 0 ;;
    *) err "未知参数: $arg"; usage; exit 1 ;;
  esac
done

# ---- 预检 ----
log "预检 Docker 环境 ..."
if ! command -v docker >/dev/null 2>&1; then
  err "未找到 docker，请先安装 Docker。"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  err "无法连接 Docker 守护进程，请确认 Docker 正在运行且当前用户有权限。"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  err "未找到 docker compose 插件，请安装 Compose v2（docker compose version）。"
  exit 1
fi
ok "Docker 与 Compose 可用。"

# ---- .env 处理 ----
if [ ! -f .env ]; then
  if [ ! -f .env.example ]; then
    err "缺少 .env 且未找到 .env.example，无法继续。"
    exit 1
  fi
  cp .env.example .env
  warn "未找到 .env，已从 .env.example 生成。"
  warn "请编辑 .env 填写 STOCK_COOKIE、MySQL 密码等密钥后重新运行本脚本。"
  exit 1
fi

# 读取 .env 中某个变量的值（忽略注释/空行，取最后一次定义）。
read_env() {
  local key="$1" line val
  line="$(grep -E "^[[:space:]]*${key}=" .env | tail -n1 || true)"
  [ -n "$line" ] || { printf '%s' ''; return; }
  val="${line#*=}"
  # 去掉两端空白与成对引号
  val="${val#"${val%%[![:space:]]*}"}"
  val="${val%"${val##*[![:space:]]}"}"
  case "$val" in
    \"*\") val="${val#\"}"; val="${val%\"}" ;;
    \'*\') val="${val#\'}"; val="${val%\'}" ;;
  esac
  printf '%s' "$val"
}

log "校验 .env 必填项 ..."
STOCK_COOKIE_VAL="$(read_env STOCK_COOKIE)"
if [ -z "$STOCK_COOKIE_VAL" ] || [ "$STOCK_COOKIE_VAL" = "your_cookie_here" ]; then
  err "STOCK_COOKIE 未配置（为空或仍是占位值 your_cookie_here）。"
  err "请在 .env 中填写有效 Cookie 后重试，否则数据抓取会返回 403。"
  exit 1
fi

MOONSHOT_VAL="$(read_env MOONSHOT_API_KEY)"
if [ -z "$MOONSHOT_VAL" ] || [ "$MOONSHOT_VAL" = "your_moonshot_api_key_here" ]; then
  warn "MOONSHOT_API_KEY 未配置，将仅运行规则引擎，不做 AI 分析。"
fi

ROOT_PW="$(read_env MYSQL_ROOT_PASSWORD)"
DB_PW="$(read_env MYSQL_PASSWORD)"
if [ "$ROOT_PW" = "stock123" ] || [ "$DB_PW" = "stock123" ]; then
  warn "检测到 MySQL 密码仍为默认值 stock123，生产环境请务必修改。"
fi
ok ".env 校验通过。"

# ---- 可选：清空旧数据卷 ----
if [ "$FRESH" -eq 1 ]; then
  warn "--fresh：执行 docker compose down -v，将删除旧的 mysql 数据卷。"
  docker compose down -v
fi

# ---- 部署 ----
if [ "$BUILD" -eq 1 ]; then
  log "构建并启动服务（docker compose up -d --build）..."
  docker compose up -d --build
else
  log "启动服务（docker compose up -d，跳过构建）..."
  docker compose up -d
fi

# ---- 等待健康 ----
SERVICES="mysql stock_rpc"
TIMEOUT=120
INTERVAL=5
elapsed=0

health_of() {
  # 返回某个 compose service 容器的健康状态字符串。
  local svc="$1" cid
  cid="$(docker compose ps -q "$svc" 2>/dev/null || true)"
  [ -n "$cid" ] || { printf '%s' 'missing'; return; }
  docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || printf '%s' 'unknown'
}

log "等待服务健康（超时 ${TIMEOUT}s）..."
while :; do
  all_ok=1
  for svc in $SERVICES; do
    st="$(health_of "$svc")"
    if [ "$st" != "healthy" ]; then
      all_ok=0
    fi
  done
  if [ "$all_ok" -eq 1 ]; then
    ok "所有关键服务已健康。"
    break
  fi
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    err "等待健康超时（${TIMEOUT}s）。当前状态："
    docker compose ps >&2 || true
    for svc in $SERVICES; do
      err "  $svc: $(health_of "$svc")"
    done
    exit 1
  fi
  sleep "$INTERVAL"
  elapsed=$((elapsed + INTERVAL))
done

# ---- 完成 ----
echo
docker compose ps
echo
RPC_PORT="$(read_env STOCK_RPC_PORT)"
[ -n "$RPC_PORT" ] || RPC_PORT="50051"
ok "部署完成，gRPC 服务监听 :${RPC_PORT}。"
