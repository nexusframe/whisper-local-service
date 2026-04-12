# API Specification — services/whisper

Dokładny kontrakt HTTP API. Klient (dowolny język) będzie pisany na podstawie
tego dokumentu, więc zero ambiguity.

## Base URL

```
http://127.0.0.1:8765
```

## Endpointy

### `POST /transcribe`

Transkrybuje audio (base64 w JSON body) i zwraca tekst.

**Request:**

```http
POST /transcribe HTTP/1.1
Host: 127.0.0.1:8765
Content-Type: application/json
```

```json
{
  "audio_base64": "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjYwLjE2LjEwMA...",
  "mime": "audio/mpeg",
  "language": "pl"
}
```

**Pola request:**

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `audio_base64` | string | **tak** | Base64-encoded audio bytes (bez prefixu data URI) |
| `mime` | string | nie | MIME type pliku (np. `audio/mpeg`, `audio/wav`, `audio/ogg`). Używane do sanity check i lepszych komunikatów błędów — faster-whisper i tak sniffuje format z magic bytes. |
| `language` | string | nie | Kod języka ISO 639-1 (`pl`, `en`, `de`, ...) lub `auto` (default) |

**Response (200 OK):**

```json
{
  "text": "tu jest transkrypcja nagrania",
  "language": "pl",
  "language_probability": 0.98,
  "duration_s": 12.4,
  "latency_ms": 842,
  "model": "large-v3"
}
```

**Pola response:**

| Pole | Typ | Opis |
|---|---|---|
| `text` | string | Czysta transkrypcja (bez timestamps) |
| `language` | string | Wykryty lub wymuszony język. **`"unknown"` jeśli audio było całkowicie silent** (model nie mógł wykryć) |
| `language_probability` | number \| null | 0.0-1.0 dla auto-detect. **`null` gdy** (1) język wymuszony przez klienta LUB (2) audio było silent |
| `duration_s` | number | Długość audio w sekundach |
| `latency_ms` | integer | Czas przetwarzania (samo transcribe, bez decode base64) |
| `model` | string | Nazwa załadowanego modelu |

**Błędy:**

| Status | Kod błędu | Kiedy |
|---|---|---|
| 400 | `invalid_request` | Niepoprawny base64, audio zero-bajtowe |
| 400 | `unsupported_mime` | Jeśli `mime` podany i spoza listy wspieranych |
| 400 | `invalid_language` | `language` kod spoza ISO 639-1 (np. `language="klingon"`) |
| 413 | `payload_too_large` | Audio base64 > `WHISPER_MAX_BYTES * 4/3` (33% overhead, ~33 MB default) LUB decoded > `WHISPER_MAX_BYTES` |
| 422 | `validation_error` | Pydantic validation failure (nieprawidłowy typ pola lub brak `audio_base64`) |
| 500 | `transcription_failed` | Model crash, OOM, inny błąd wewnętrzny |
| 503 | `model_not_loaded` | Service uruchomiony, ale model jeszcze nie załadowany (lub warmup w toku) |
| 504 | `transcription_timeout` | Transkrypcja przekroczyła `WHISPER_REQUEST_TIMEOUT_S` (default 300) |

**Format błędu:**

```json
{
  "error": "invalid_request",
  "message": "Field 'audio_base64' contains invalid base64 data",
  "details": { }
}
```

---

### `GET /ping`

Lightweight service status check — nie wymaga załadowanego modelu.

**Request:**

```http
GET /ping HTTP/1.1
Host: 127.0.0.1:8765
```

**Response (200 OK):**

```json
{
  "status": "ok"
}
```

**Zastosowanie:**

Jeśli serwer startuje i model się ładuje, `/health` zwraca 503 (model_loaded=false).
Klient może `/ping` sprawdzić czy serwer w ogóle żyje zanim czeka na `/health` 200.

**Statusy HTTP:**
- `200 OK` — serwer uruchomiony
- Jeśli nie odpowiada → serwer nie żyje lub nie uruchomiony

---

### `GET /health`

Health check — czy service żyje i czy model załadowany + warm.

**Request:**

```http
GET /health HTTP/1.1
Host: 127.0.0.1:8765
```

**Response (200 OK, model załadowany — warmup complete lub in-progress):**

```json
{
  "model_loaded": true,
  "warmup_complete": true,
  "model_name": "large-v3",
  "device": "cuda",
  "compute_type": "int8_float16",
  "uptime_s": 3621
}
```

**Response (200 OK, warmup in progress — model loaded ale jeszcze warming up):**

```json
{
  "model_loaded": true,
  "warmup_complete": false,
  "model_name": "large-v3",
  "device": "cuda",
  "compute_type": "int8_float16",
  "uptime_s": 12
}
```

**Pola:**

| Pole | Typ | Opis |
|---|---|---|
| `model_loaded` | boolean | Czy model jest w pamięci (ładowanie zakończone) |
| `warmup_complete` | boolean | Czy warmup test call się skończył bez błędu. Brak tego pola = assume `false` (dla backwards compat). |
| `model_name` | string | Załadowany model |
| `device` | `"cuda"` \| `"cpu"` | Gdzie liczy |
| `compute_type` | string | Auto-wybrane quantization (int8, int8_float16, float16, float32) |
| `uptime_s` | integer | Jak długo service chodzi |

**Statusy HTTP:**

- `200 OK` — model załadowany (`model_loaded=true`). Jeśli `warmup_complete=true`: service ready. Jeśli `warmup_complete=false`: czekaj lub accept że /transcribe będzie slow.
- `503 Service Unavailable` — model nie załadowany jeszcze (ładowanie w toku)

Klient używa `/health` na starcie pętli — jeśli `200` nie przyjdzie → fail-fast
z komunikatem.

**Nie ma pola `status`** — HTTP status code niesie tę informację.

**Nie ma pól `vram_used_mb` ani `transcriptions_total`** — VRAM debugging przez
`nvidia-smi` w terminalu, liczniki requestów w logach. Minimal surface area.

---

## Przykład użycia (curl)

```bash
# Health check
curl -s http://localhost:8765/health | jq

# Transcribe (audio z pliku)
AUDIO_B64=$(base64 -w0 < sample.mp3)
curl -s -X POST http://localhost:8765/transcribe \
  -H "Content-Type: application/json" \
  -d "{\"audio_base64\":\"$AUDIO_B64\",\"language\":\"pl\"}" \
  | jq
```

## Przykład użycia (Python)

```python
import base64
import requests

with open("sample.mp3", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

res = requests.post(
    "http://127.0.0.1:8765/transcribe",
    json={"audio_base64": audio_b64, "language": "pl"},
    timeout=600,
)
res.raise_for_status()
data = res.json()
print(f"[{data['language']}, {data['duration_s']}s] {data['text']}")
```

## Przykład użycia (Node.js)

```js
import { readFile } from 'node:fs/promises';

const audio = await readFile('sample.mp3');
const audio_base64 = audio.toString('base64');

const res = await fetch('http://127.0.0.1:8765/transcribe', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    audio_base64,
    language: 'pl',
  }),
});

if (!res.ok) {
  const err = await res.json();
  throw new Error(`Whisper service: ${err.error} — ${err.message}`);
}

const { text, language, duration_s, latency_ms } = await res.json();
console.log(`[${language}, ${duration_s}s, ${latency_ms}ms] ${text}`);
```

## Wspierane kody języków

`language` field akceptuje:
- `"auto"` — model wykrywa język automatycznie (default)
- Kody ISO 639-1 (~200): `"pl"`, `"en"`, `"de"`, `"fr"`, `"es"`, `"it"`, `"pt"`, `"ru"`, `"zh"`, `"ja"`, `"ko"`, itd.

Pełna lista: [ISO 639-1 codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)

Inne formaty (np. `"zh-CN"`, `"yue"`) NIE są wspierane — zwrócą błąd `400 invalid_language`.

---

## Wspierane formaty audio

Lista MIME types które service akceptuje (gdy klient podaje `mime`):

| MIME | Rozszerzenie | Notes |
|---|---|---|
| `audio/mpeg` | `.mp3` | Najpopularniejsze, podstawowe |
| `audio/wav` | `.wav` | Bez strat, duży rozmiar |
| `audio/x-wav` | `.wav` | Wariant MIME |
| `audio/ogg` | `.ogg` | Vorbis/Opus |
| `audio/opus` | `.opus` | |
| `audio/flac` | `.flac` | |
| `audio/x-m4a` | `.m4a` | AAC w MP4 container |
| `audio/mp4` | `.m4a`, `.mp4` | |
| `audio/webm` | `.webm` | |

Jeśli `mime` podany i spoza listy → `400 unsupported_mime`. Jeśli `mime`
pominięty → próbujemy transkrybować, faster-whisper/ffmpeg i tak sam
sniffuje magic bytes.

## Environment variables (konfiguracja)

| Zmienna | Default | Opis |
|---|---|---|
| `WHISPER_HOST` | `127.0.0.1` | Bind address — NIE zmieniać na `0.0.0.0` bez auth |
| `WHISPER_PORT` | `8765` | Port HTTP |
| `WHISPER_MODEL` | `large-v3` | Model do załadowania przy starcie |
| `WHISPER_DEVICE` | `auto` | `auto`, `cuda`, `cpu` |
| `WHISPER_COMPUTE_TYPE` | `auto` | `auto`, `int8`, `int8_float16`, `float16`, `float32`. `auto` pozwala faster-whisper wybrać best-available. |
| `WHISPER_MAX_BYTES` | `26214400` (25 MB) | Max rozmiar audio po decode |
| `WHISPER_REQUEST_TIMEOUT_S` | `300` | Timeout pojedynczej transkrypcji (server-side) |
| `WHISPER_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
