#!/bin/bash
set -e

PORT=${WHISPER_PORT:-8765}
HOST=${WHISPER_HOST:-127.0.0.1}

# Pre-check: is port already in use?
if command -v lsof &> /dev/null; then
  if lsof -i :$PORT &> /dev/null; then
    echo "Error: Port $PORT is already in use."
    echo "Kill the process and retry: lsof -i :$PORT"
    exit 1
  fi
elif command -v ss &> /dev/null; then
  if ss -tlnp 2>/dev/null | grep -q ":$PORT"; then
    echo "Error: Port $PORT is already in use."
    echo "Kill the process and retry: ss -tlnp | grep $PORT"
    exit 1
  fi
fi

# Load .env and activate venv
set -a
source .env 2>/dev/null || true
set +a
source .venv/bin/activate
exec uvicorn server:app --host $HOST --port $PORT
