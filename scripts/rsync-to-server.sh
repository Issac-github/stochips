#!/usr/bin/env bash
#
# Sync this repository to a server with rsync.
#
# Usage:
#   ./scripts/rsync-to-server.sh root@1.2.3.4:/root/stochips/
#   ./scripts/rsync-to-server.sh root@server:/root/stochips/ --delete
#
# Notes:
# - .env is intentionally excluded so server secrets are not overwritten.
# - Generated protobuf Go code is kept because stock_rpc builds from it.
#
set -euo pipefail

cd "$(cd "$(dirname "$0")/.." && pwd)"

TARGET="${1:-}"
DELETE_FLAG="${2:-}"

if [ -z "$TARGET" ]; then
  cat >&2 <<'EOF'
Usage:
  ./scripts/rsync-to-server.sh <user@host:/root/stochips/> [--delete]

Example:
  ./scripts/rsync-to-server.sh root@8.163.22.74:/root/stochips/
EOF
  exit 1
fi

if [ -n "$DELETE_FLAG" ] && [ "$DELETE_FLAG" != "--delete" ]; then
  echo "Unknown option: $DELETE_FLAG" >&2
  exit 1
fi

if [ "$DELETE_FLAG" = "--delete" ]; then
  set -- --delete
else
  set --
fi

rsync -avz "$@" \
  --exclude='.env' \
  --exclude='.git/' \
  --exclude='.trellis/' \
  --exclude='.agents/' \
  --exclude='.claude/' \
  --exclude='.codex/' \
  --exclude='.superpowers/' \
  --exclude='.vscode/' \
  --exclude='docs/superpowers/' \
  --exclude='front/node_modules/' \
  --exclude='front/out/' \
  --exclude='front/dist/' \
  --exclude='front/.eslintcache' \
  --exclude='services/agent/.venv/' \
  --exclude='services/agent/__pycache__/' \
  --exclude='services/agent/.pytest_cache/' \
  --exclude='services/agent/logs/' \
  --exclude='services/agent/stock_agent.log' \
  --exclude='**/__pycache__/' \
  --exclude='**/.DS_Store' \
  ./ "$TARGET"
