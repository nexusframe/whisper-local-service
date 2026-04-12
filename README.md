# Whisper — Local Speech-to-Text Service

A lightweight HTTP microservice for speech-to-text transcription using OpenAI's Whisper model with CTranslate2 acceleration. Runs entirely on localhost with GPU support (CUDA) and CPU fallback. ~3 GB VRAM with `large-v3 int8` quantization.

## Features

- **Multi-language**: ~190 languages (ISO 639-1 codes)
- **Audio formats**: MP3, WAV, OGG, FLAC, WebM, M4A, Opus
- **GPU acceleration**: CUDA with int8 quantization (~3 GB VRAM)
- **CPU fallback**: Works on CPU if CUDA unavailable (slower)
- **Structured logging**: JSON lines with request tracing
- **Comprehensive validation**: 7-step fail-fast pipeline
- **Language-agnostic**: HTTP API, works from any language/tool

## Requirements

- **Python**: 3.10 or higher
- **VRAM**: 8 GB (fits `large-v3 int8`)
  - GPU with CUDA 12.x (optional, CUDA driver required)
  - cuDNN 9 (optional, speeds up transcription)
  - CPU: Works but ~10-30× slower
- **Storage**: ~3 GB for model cache

## Quick Start

### One-Time Setup

```bash
cd services/whisper
./setup.sh
```

This will:
1. Check Python version (≥3.10)
2. Detect CUDA availability
3. Create `.venv/` virtual environment
4. Install dependencies
5. Download `large-v3` model to `~/.cache/huggingface/` (~3 GB, takes 5-10 min)

### Start the Service

```bash
./start.sh
```

Service runs on `http://127.0.0.1:8765`. Response:

```
{"ts": "2026-04-08T20:00:00Z", "level": "INFO", "msg": "Loading model large-v3 on cuda..."}
{"ts": "2026-04-08T20:00:03Z", "level": "INFO", "msg": "Model loaded"}
{"ts": "2026-04-08T20:00:04Z", "level": "INFO", "msg": "Warmup complete"}
{"ts": "2026-04-08T20:00:05Z", "level": "INFO", "msg": "Whisper service ready", "model": "large-v3"}
```

### Health Check

```bash
curl http://127.0.0.1:8765/health | jq
{
  "model_loaded": true,
  "warmup_complete": true,
  "model_name": "large-v3",
  "device": "cuda",
  "compute_type": "int8",
  "uptime_s": 42
}
```

## API

### `GET /ping`

Lightweight status check (no model required).

```bash
curl http://127.0.0.1:8765/ping
{"status": "ok"}
```

### `GET /health`

Full service readiness check.

```bash
curl http://127.0.0.1:8765/health
{
  "model_loaded": true,
  "warmup_complete": true,
  "model_name": "large-v3",
  "device": "cuda",
  "compute_type": "int8",
  "uptime_s": 42
}
```

### `POST /transcribe`

Transcribe audio (base64-encoded).

**Request:**

```bash
AUDIO_B64=$(base64 -w0 < audio.mp3)
curl -X POST http://127.0.0.1:8765/transcribe \
  -H "Content-Type: application/json" \
  -d "{\"audio_base64\": \"$AUDIO_B64\", \"language\": \"pl\"}"
```

**Response (200 OK):**

```json
{
  "text": "W Szczebrzeszynie chrząszcz brzmi...",
  "language": "pl",
  "language_probability": null,
  "duration_s": 9.21,
  "latency_ms": 420,
  "model": "large-v3"
}
```

**Request fields:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `audio_base64` | string | ✓ | Base64-encoded audio bytes (no data URI prefix) |
| `mime` | string | — | MIME type (e.g., `audio/mpeg`, `audio/wav`). Optional; sniffing via magic bytes |
| `language` | string | — | ISO 639-1 code (`pl`, `en`, `de`, ...) or `auto` (default). Auto-detects if not specified. |

**Response fields:**

| Field | Type | Notes |
|-------|------|-------|
| `text` | string | Transcribed text (cleaned, no timestamps) |
| `language` | string | Detected or forced language code, or `"unknown"` if silent audio |
| `language_probability` | float \| null | Confidence (0.0-1.0) for auto-detect; `null` if language was forced |
| `duration_s` | float | Audio duration in seconds |
| `latency_ms` | integer | Transcription time (ms) |
| `model` | string | Model name (`large-v3`, etc.) |

**Error responses:**

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | `invalid_request` | Empty audio or invalid base64 |
| 400 | `invalid_language` | Language code not ISO 639-1 |
| 400 | `unsupported_mime` | MIME type not supported |
| 413 | `payload_too_large` | Audio exceeds 25 MB limit |
| 503 | `model_not_loaded` | Model still loading |
| 504 | `transcription_timeout` | Audio took >300s to process |
| 500 | `transcription_failed` | Model error (OOM, crash, etc.) |

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `WHISPER_HOST` | `127.0.0.1` | Bind address (localhost only) |
| `WHISPER_PORT` | `8765` | HTTP port |
| `WHISPER_MODEL` | `large-v3` | Model (`large-v3`, `large-v3-turbo`, etc.) |
| `WHISPER_DEVICE` | `auto` | `auto`, `cuda`, `cpu` |
| `WHISPER_COMPUTE_TYPE` | `auto` | `auto`, `int8`, `int8_float16`, `float16`, `float32` |
| `WHISPER_MAX_BYTES` | `26214400` | Max audio size (bytes, ~25 MB) |
| `WHISPER_REQUEST_TIMEOUT_S` | `300` | Max transcription time (seconds, 5 min) |
| `WHISPER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Troubleshooting

### CUDA not found — device shows "cpu"

**Symptom:** Logs show `"device": "cpu"`, transcription very slow (30s+/min audio)

**Solution:**
- Install NVIDIA driver: `nvidia-smi` should show your GPU
- Or accept CPU (slow but works)

### cuDNN missing — `libcudnn.so.8: cannot open shared object file`

**Symptom:** Warning during startup, transcription slower than expected

**Solution (Ubuntu):**
```bash
sudo apt update && sudo apt install libcudnn9
```

Or set library path if custom cuDNN install:
```bash
export LD_LIBRARY_PATH=/path/to/cudnn/lib:$LD_LIBRARY_PATH
./start.sh
```

### CUDA Out of Memory (OOM)

**Symptom:** Error during warmup: `CUDA out of memory`

**Solution:**
1. Check if another process uses GPU: `nvidia-smi`
2. If GPU is free but OOM anyway, fallback to faster model (loses 2-5% quality):
   ```bash
   WHISPER_MODEL=large-v3-turbo ./start.sh
   ```
   (~1 GB VRAM savings)
3. Last resort: use CPU
   ```bash
   WHISPER_DEVICE=cpu ./start.sh
   ```

### Port 8765 already in use

**Symptom:** `Address already in use :8765`

**Solution:**
```bash
lsof -i :8765           # Find process using port
kill <PID>              # Kill it
./start.sh              # Restart service
```

Or use different port:
```bash
WHISPER_PORT=8766 ./start.sh
```

### Model download fails or hangs

**Symptom:** `setup.sh` stuck during model download

**Solution:**
```bash
# Use HuggingFace mirror
HF_ENDPOINT=https://huggingface.co ./setup.sh

# Or check internet connectivity
ping github.com
```

### First request is slow

**Normal behavior:** First request after startup takes 2-3× longer due to GPU kernel compilation. Subsequent requests are faster.

Run `./start.sh` and wait for log `"msg": "Whisper service ready"` before making requests.

## Examples

### Python

```python
import base64
import requests

audio = open("audio.mp3", "rb").read()
resp = requests.post(
    "http://127.0.0.1:8765/transcribe",
    json={
        "audio_base64": base64.b64encode(audio).decode(),
        "language": "pl"
    },
    timeout=600
)
print(resp.json()["text"])
```

### Node.js

```javascript
const audio = fs.readFileSync("audio.mp3");
const audioB64 = audio.toString("base64");

const res = await fetch("http://127.0.0.1:8765/transcribe", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ audio_base64: audioB64, language: "pl" })
});

console.log((await res.json()).text);
```

### cURL

```bash
AUDIO=$(base64 -w0 < audio.mp3)
curl -X POST http://127.0.0.1:8765/transcribe \
  -H "Content-Type: application/json" \
  -d "{\"audio_base64\": \"$AUDIO\", \"language\": \"pl\"}"
```

## Testing

Run pytest suite:

```bash
# Fast tests (skip 6-min timeout test)
pytest tests/ -v -m "not slow"

# Only timeout test (takes 6+ min)
pytest tests/ -v -m slow

# All tests
pytest tests/ -v
```

## Architecture

See `PLAN/` directory for:
- `README.md` — project overview
- `decisions.md` — design decisions (17 D-points)
- `api_spec.md` — detailed API specification
- `phases.md` — implementation phases

## License

This service wraps OpenAI Whisper (MIT) and CTranslate2 (MIT). Test fixtures from Wikimedia Commons under CC BY/CC BY-SA.

## See Also

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2 Whisper wrapper
- [OpenAI Whisper](https://github.com/openai/whisper) — Original model
- [CTranslate2](https://github.com/OpenNMT/CTranslate2) — Fast inference engine
