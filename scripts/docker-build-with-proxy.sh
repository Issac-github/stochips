#!/usr/bin/env bash
# Compatibility entrypoint. Use stochips-with-proxy.sh for new commands.
set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)"
echo "Note: docker-build-with-proxy.sh is kept for compatibility; use stochips-with-proxy.sh for new commands." >&2
exec ./stochips-with-proxy.sh "$@"
