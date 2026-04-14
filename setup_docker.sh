#!/bin/bash
set -e

IMAGE="whisper-stt"
MODEL=${WHISPER_MODEL:-large-v3-turbo}

echo "Building whisper-stt image with model: ${MODEL}"
echo "This will download ~3 GB model during build."
echo

docker build -t "$IMAGE" --build-arg "WHISPER_MODEL=${MODEL}" .

echo
echo "Done. Run with: ./start_docker.sh"


# To override the default model, set the WHISPER_MODEL environment variable before running this script.
# WHISPER_MODEL=large-v3 ./setup_docker.sh