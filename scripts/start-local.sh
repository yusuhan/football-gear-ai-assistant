#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v npm >/dev/null || { echo "npm is required" >&2; exit 1; }

cleanup() {
  trap - INT TERM EXIT
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import fastapi, uvicorn, pydantic" 2>/dev/null; then
  "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"
fi

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  (cd "$ROOT_DIR/frontend" && npm install)
fi

export APP_ENV="${APP_ENV:-local}"
export DATABASE_PATH="${DATABASE_PATH:-$ROOT_DIR/data/football_gear.db}"
export BACKEND_CORS_ORIGIN="${BACKEND_CORS_ORIGIN:-http://localhost:3000}"
export NO_PROXY="127.0.0.1,localhost,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"

cd "$ROOT_DIR"
"$VENV_DIR/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
npm run dev -- --hostname 127.0.0.1 &
FRONTEND_PID=$!

cd "$ROOT_DIR"
"$VENV_DIR/bin/python" scripts/smoke_test.py --wait

printf '\nFootball Gear AI Assistant is ready:\n'
printf '  Chat:  http://localhost:3000\n'
printf '  Admin: http://localhost:3000/admin/handoffs\n'
printf '  API:   http://localhost:8000/docs\n\n'

wait "$BACKEND_PID" "$FRONTEND_PID"
