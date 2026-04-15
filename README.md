# Whisper — Local Speech-to-Text Service

HTTP microservice for audio transcription using faster-whisper (CTranslate2). Localhost only, GPU accelerated (~3 GB VRAM with `large-v3 int8`), CPU fallback.

## Quick Start

```bash
# One-time setup (venv + model download, ~5-10 min)
./setup.sh

# Start service
./start.sh

# Health check
curl http://127.0.0.1:8765/health | jq
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ping` | GET | Service alive check (no model required) |
| `/health` | GET | Full readiness check (model loaded, warmup status) |
| `/transcribe` | POST | Transcribe base64-encoded audio |

### Transcribe

```bash
AUDIO=$(base64 -w0 < audio.mp3)
curl -X POST http://127.0.0.1:8765/transcribe \
  -H "Content-Type: application/json" \
  -d "{\"audio_base64\": \"$AUDIO\", \"language\": \"pl\", \"timestamps\": true}"
```

Key request fields: `audio_base64` (required), `language`, `timestamps`, `initial_prompt`.

Response: `text`, `segments` (when timestamps=true), `language`, `duration_s`, `latency_ms`.

Full API reference: [docs/api.md](docs/api.md)

## Testing

```bash
# Fast tests (23 tests, ~20s)
pytest tests/ -v -m "not slow"

# All tests including timeout (adds ~6 min)
pytest tests/ -v
```

## Docs

- [API Reference](docs/api.md) — endpoints, request/response fields, errors, examples
- [Configuration](docs/configuration.md) — environment variables, models, compute types
- [Troubleshooting](docs/troubleshooting.md) — CUDA, OOM, port conflicts, model download

## Architecture

Design docs in `PLAN/`: [overview](PLAN/README.md), [decisions](PLAN/decisions.md), [API spec](PLAN/api_spec.md), [phases](PLAN/phases.md).

## License

Wraps OpenAI Whisper (MIT) and CTranslate2 (MIT). Test fixtures from Wikimedia Commons (CC BY/CC BY-SA).
