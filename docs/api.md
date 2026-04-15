# API Reference

Base URL: `http://127.0.0.1:8765`

## `GET /ping`

Lightweight status check (no model required).

```bash
curl http://127.0.0.1:8765/ping
{"status": "ok"}
```

## `GET /health`

Full service readiness check.

```bash
curl http://127.0.0.1:8765/health
```

```json
{
  "model_loaded": true,
  "warmup_complete": true,
  "model_name": "large-v3",
  "device": "cuda",
  "compute_type": "int8",
  "uptime_s": 42
}
```

| Field | Type | Notes |
|-------|------|-------|
| `model_loaded` | bool | Model in memory |
| `warmup_complete` | bool | Warmup inference done |
| `model_name` | string | Loaded model |
| `device` | `"cuda"` \| `"cpu"` | Compute device |
| `compute_type` | string | Quantization type |
| `uptime_s` | integer | Seconds since startup |

HTTP 503 if model still loading.

## `POST /transcribe`

Transcribe base64-encoded audio.

### Request

```bash
AUDIO_B64=$(base64 -w0 < audio.mp3)
curl -X POST http://127.0.0.1:8765/transcribe \
  -H "Content-Type: application/json" \
  -d "{\"audio_base64\": \"$AUDIO_B64\", \"language\": \"pl\"}"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `audio_base64` | string | yes | Base64-encoded audio (no data URI prefix) |
| `mime` | string | no | MIME type (`audio/mpeg`, `audio/wav`, etc.). Optional; format sniffed from magic bytes |
| `language` | string | no | ISO 639-1 code (`pl`, `en`, `de`, ...) or `auto` (default) |
| `initial_prompt` | string | no | Context hint for domain vocabulary (e.g. `"LangChain, FAISS, RAG"`) |
| `timestamps` | bool | no | Return segments with start/end times (default `false`) |

### Response (200 OK)

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

With `"timestamps": true`:

```json
{
  "text": "W Szczebrzeszynie chrząszcz brzmi...",
  "segments": [
    {"start": 0.0, "end": 3.44, "text": "W Szczebrzeszynie"},
    {"start": 3.44, "end": 9.21, "text": "chrząszcz brzmi..."}
  ],
  "language": "pl",
  "language_probability": null,
  "duration_s": 9.21,
  "latency_ms": 420,
  "model": "large-v3"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `text` | string | Full transcription (all segments joined) |
| `segments` | array \| null | Only present when `timestamps=true`. Each: `{start, end, text}` (seconds) |
| `language` | string | Detected/forced language, `"unknown"` if silent |
| `language_probability` | float \| null | 0.0-1.0 for auto-detect; `null` if language forced |
| `duration_s` | float | Audio duration (seconds) |
| `latency_ms` | integer | Processing time (ms) |
| `model` | string | Model name |

### Errors

| Status | Error | Meaning |
|--------|-------|---------|
| 400 | `invalid_request` | Empty audio or invalid base64 |
| 400 | `invalid_language` | Language code not ISO 639-1 |
| 400 | `unsupported_mime` | MIME type not in supported list |
| 413 | `payload_too_large` | Audio exceeds 25 MB |
| 503 | `model_not_loaded` | Model still loading |
| 504 | `transcription_timeout` | Transcription exceeded 300s |
| 500 | `transcription_failed` | Model error (OOM, crash) |

Error format:

```json
{
  "error": "invalid_request",
  "message": "Audio is empty",
  "details": {}
}
```

### Supported MIME types

`audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/x-wav`, `audio/ogg`, `audio/opus`, `audio/flac`, `audio/webm`, `audio/m4a`

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
        "language": "pl",
        "timestamps": True,
        "initial_prompt": "LangChain, FAISS, embeddingi",
    },
    timeout=600,
)
data = resp.json()
print(data["text"])
for seg in data.get("segments", []):
    print(f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text']}")
```

### Node.js

```javascript
import { readFile } from 'node:fs/promises';

const audio = await readFile('audio.mp3');
const res = await fetch('http://127.0.0.1:8765/transcribe', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    audio_base64: audio.toString('base64'),
    language: 'pl',
    timestamps: true,
  }),
});
const { text, segments } = await res.json();
console.log(text);
```

### cURL

```bash
AUDIO=$(base64 -w0 < audio.mp3)
curl -X POST http://127.0.0.1:8765/transcribe \
  -H "Content-Type: application/json" \
  -d "{\"audio_base64\": \"$AUDIO\", \"language\": \"pl\", \"timestamps\": true}"
```
