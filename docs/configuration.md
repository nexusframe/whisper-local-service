# Configuration

All settings via environment variables. Set in `.env` or pass inline.

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `WHISPER_HOST` | `127.0.0.1` | Bind address (localhost only, do not change to `0.0.0.0`) |
| `WHISPER_PORT` | `8765` | HTTP port |
| `WHISPER_MODEL` | `large-v3` | Model name (see Models below) |
| `WHISPER_DEVICE` | `auto` | `auto`, `cuda`, `cpu` |
| `WHISPER_COMPUTE_TYPE` | `auto` | `auto`, `int8`, `int8_float16`, `float16`, `float32` |
| `WHISPER_MAX_BYTES` | `26214400` | Max audio size after base64 decode (~25 MB) |
| `WHISPER_REQUEST_TIMEOUT_S` | `300` | Max transcription time (seconds) |
| `WHISPER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Models

| Model | Params | VRAM (int8) | Quality | Speed |
|-------|--------|-------------|---------|-------|
| `large-v3` | 1.5B | ~3 GB | best | baseline |
| `large-v3-turbo` | 809M | ~2 GB | ~95-97% of v3 | ~2x faster |
| `medium` | 769M | ~1.5 GB | good | fast |
| `small` | 244M | ~0.5 GB | decent | very fast |

Default is `large-v3`. Use `large-v3-turbo` if VRAM is tight (saves ~1 GB, minimal quality loss).

## Compute Types

| Type | VRAM | Quality | Notes |
|------|------|---------|-------|
| `float32` | highest | baseline | CPU default |
| `float16` | ~50% of f32 | ~identical | GPU only |
| `int8_float16` | ~25% of f32 | minimal loss | GPU default with `auto` |
| `int8` | lowest | minimal loss | CPU-friendly |

`auto` selects the best option for your hardware.
