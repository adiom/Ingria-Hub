#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-31337}"
HOST="${HOST:-0.0.0.0}"

cd "$(dirname "$0")"

PIDS="$(lsof -ti "tcp:${PORT}" 2>/dev/null || true)"
if [ -n "${PIDS}" ]; then
    echo "Освобождаю порт ${PORT}: убиваю процессы ${PIDS//$'\n'/ }"
    kill -9 ${PIDS} 2>/dev/null || true
else
    echo "Порт ${PORT} свободен"
fi

if [ -x "venv/bin/uvicorn" ]; then
    UVICORN="venv/bin/uvicorn"
else
    UVICORN="uvicorn"
fi

exec "${UVICORN}" main:app --reload --host "${HOST}" --port "${PORT}" "$@"
