FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

ARG WHISPER_MODEL=large-v3
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', compute_type='auto')"

COPY *.py .

ENV WHISPER_HOST=0.0.0.0
ENV WHISPER_PORT=8765
ENV WHISPER_MODEL=${WHISPER_MODEL}
ENV WHISPER_DEVICE=auto
ENV WHISPER_COMPUTE_TYPE=auto
ENV WHISPER_MAX_BYTES=26214400
ENV WHISPER_REQUEST_TIMEOUT_S=300
ENV WHISPER_LOG_LEVEL=INFO

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/ping')" || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765"]
