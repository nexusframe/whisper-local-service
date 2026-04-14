#!/bin/bash
set -e

IMAGE="whisper-stt"
PORT=${WHISPER_PORT:-8765}
CONTAINER_NAME="whisper-stt"

# Stop existing container if running
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
  echo "Stopping existing container..."
  docker stop "$CONTAINER_NAME" >/dev/null
fi

exec docker run --rm --gpus all \
  --name "$CONTAINER_NAME" \
  -p "127.0.0.1:${PORT}:8765" \
  "$IMAGE"
