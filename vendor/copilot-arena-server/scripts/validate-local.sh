#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_URL="${ARC_ARENA_SERVER_URL:-http://127.0.0.1:8080}"

cd "$ROOT_DIR"

python3 -m py_compile \
  app.py \
  constants.py \
  src/local_config.py \
  src/local_scores.py \
  src/privacy.py \
  src/sqlite_client.py \
  src/user_repository.py

if command -v curl >/dev/null 2>&1; then
  if curl --fail --silent --max-time 2 "$SERVER_URL/list_models" >/dev/null; then
    printf 'arena server reachable: %s\n' "$SERVER_URL"
  else
    printf 'arena server not reachable at %s; syntax-only validation passed\n' "$SERVER_URL"
  fi

  if [ "${ARC_ARENA_SMOKE_CREATE_PAIR:-0}" = "1" ]; then
    curl --fail --silent --max-time 30 \
      -H 'Content-Type: application/json' \
      -X POST "$SERVER_URL/create_pair" \
      --data '{"prefix":"print(","suffix":")","userId":"arc-local-validation","privacy":"Private","modelTags":[]}' >/dev/null
    printf 'arena /create_pair smoke passed: %s\n' "$SERVER_URL"
  fi
else
  printf 'curl not found; syntax-only validation passed\n'
fi
