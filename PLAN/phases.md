# Phases — implementacja services/whisper

Fazy z kryteriami akceptacji. Każda faza = jedna testowalna porcja pracy.
Zaliczaj fazę dopiero gdy kryterium akceptacji jest spełnione (odpal
komendę, sprawdź output).

6 faz, każda z wyraźnym celem i acceptance criterion.

## Phase 1 — Fundament i setup

**Cel:** czysta struktura katalogów, zainstalowane dependencies, model
pobrany lokalnie, fixtures gotowe.

**Do zrobienia:**

- [ ] Stwórz `services/whisper/requirements.txt`:
  ```
  faster-whisper>=1.0.3,<2.0
  fastapi>=0.110
  uvicorn[standard]>=0.27
  pydantic>=2.5
  numpy>=1.24
  ```
- [ ] Stwórz `services/whisper/requirements-dev.txt`:
  ```
  -r requirements.txt
  pytest>=8.0
  requests>=2.31
  ```
- [ ] Stwórz `services/whisper/.env.example` z wszystkimi zmiennymi
  z `PLAN/api_spec.md` sekcja Environment variables
- [ ] Stwórz `services/whisper/.gitignore`:
  ```
  .venv/
  __pycache__/
  *.pyc
  .env
  *.log
  .pytest_cache/
  .pytest_cache/
  ```
- [ ] Napisz `services/whisper/setup.sh`:
  - sprawdza `python3 --version` ≥ 3.10, fail z czytelnym komunikatem jeśli niższy
  - CUDA check:
    ```bash
    python3 << 'EOF'
    import torch
    if torch.cuda.is_available():
      print(f"✓ CUDA {torch.version.cuda}")
    else:
      print("⚠ CUDA not available. Will use CPU (slow, but OK).")
    EOF
    ```
  - pre-check cuDNN: próbuje załadować `libcudnn` przez ctypes; jeśli brak
    i `nvidia-smi` widzi GPU → głośny warning „⚠ cuDNN missing. See README troubleshooting"
  - tworzy venv w `services/whisper/.venv/` (dot-prefix)
  - `source .venv/bin/activate && pip install -r requirements.txt`
  - pre-download modelu:
    `python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', compute_type='int8')"`
  - ładna informacja na końcu co dalej (uruchomić `./start.sh`)
- [ ] `chmod +x setup.sh`
- [ ] Stwórz `services/whisper/validate_model.py`:
  - Pre-flight check: czy model jest w cache (`~/.cache/huggingface/`)
  - Try-load na CPU (nie CUDA, żeby nie wkładać GPU w startup check)
  - Exit code 0 = OK, exit code 1 = missing/corrupt
  - Przydatne dla `start.sh` pre-check
- [ ] Weryfikacja fixtures są w repo (`fixtures/pl_chrzaszcz.ogg`,
  `fixtures/en_fox.ogg`, `fixtures/en_rolling_stone.ogg`, `fixtures/README.md`)
  — powinny już być committed przez tę sesję

**Kryterium akceptacji:**
```
$ cd services/whisper
$ ./setup.sh
✓ Python 3.10+
✓ CUDA 12.4 available
✓ Creating venv...
✓ Installing dependencies...
✓ Downloading model large-v3 (3.2 GB)...
Setup complete. To start the service: ./start.sh

$ ls .venv/
bin/ include/ lib/ lib64/ pyvenv.cfg

$ ls fixtures/
en_fox.ogg  en_rolling_stone.ogg  pl_chrzaszcz.ogg  README.md  pl_alphabet.ogg  pl_smartfon.ogg  en_uk_north_wind.ogg  en_us_election.ogg

$ python validate_model.py
✓ Model large-v3 loaded successfully
```

HuggingFace cache (`~/.cache/huggingface/`) powinien zawierać `large-v3`
(~3 GB) po ukończeniu.

## Phase 2 — Scaffold FastAPI + /health + warmup (z modularyzacją)

**Cel:** serwer uruchamia się, model ładuje się w lifespan, warmup call
wykonany, `/health` zwraca `200` dopiero po warmupie. Kod zmodularyzowany
(D16) żeby każdy plik < 200 linii.

**Do zrobienia:**

- [ ] Stwórz `services/whisper/models.py` (~40 linii):
  - `TranscribeRequest` — pydantic model
  - `TranscribeResponse` — pydantic model
  - `ErrorResponse` — pydantic model
  - Type hints, `Config(json_schema_extra=...)` dla Swagger docs

- [ ] Stwórz `services/whisper/logging_setup.py` (~30 linii, D17):
  - `JSONFormatter` — custom logging formatter
  - `setup_logging()` function — configure logger z JSON output
  - Handler na `sys.stdout` (nie file)
  - Respektuj `WHISPER_LOG_LEVEL` env var

- [ ] Stwórz `services/whisper/transcribe.py` (~50 linii):
  - `WhisperExecutor` class:
    - `__init__()` — initialize state
    - `async startup()` — load model, warmup
    - `async shutdown()` — cleanup executor
    - `async transcribe(request: TranscribeRequest)` — async wrapper
    - `_do_transcribe(audio_bytes, language)` — sync method (runs in executor)
  - Używaj `ThreadPoolExecutor(max_workers=1)` + `run_in_executor()`
  - Warmup na `numpy.zeros(32000)` (2s ciszy)

- [ ] Stwórz `services/whisper/server.py` (~60 linii):
  - `from models import *`
  - `from transcribe import WhisperExecutor`
  - `from logging_setup import setup_logging`
  - FastAPI app z `@app.lifespan` async context manager
  - `GET /ping` — lightweight endpoint (200 OK, nie wymaga modelu)
    - Zastosowanie: klient sprawdza czy serwer żyje zanim czeka na `/health`
    - Response: `{"status": "ok"}`
  - `GET /health` — zwraca JSON z `model_loaded`, `model_name`, `device`, `compute_type`, `uptime_s`
    - Returns `503` jeśli model nie załadowany (w toku warmup)
  - `POST /transcribe` — placeholder (implementacja w Phase 3)
  - W startup: `executor = WhisperExecutor(); await executor.startup(); app.state.executor = executor`
  - W shutdown: `await app.state.executor.shutdown()`

- [ ] Napisz `services/whisper/start.sh`:
  - `set -e`
  - Pre-check model: `python validate_model.py || { echo "❌ Run ./setup.sh"; exit 1; }`
  - Pre-check port: `lsof -i :${WHISPER_PORT:-8765}` → exit 1 jeśli zajęty
  - `source .venv/bin/activate`
  - Export env vars z `.env` jeśli istnieje (`.env.example` has default values)
  - `exec uvicorn server:app --host ${WHISPER_HOST:-127.0.0.1} --port ${WHISPER_PORT:-8765}`

- [ ] `chmod +x start.sh`

- [ ] Stwórz `services/whisper/start.sh`:
  - Pre-check: czy port 8765 jest wolny (przez `lsof -i :8765` lub `ss -tlnp`)
  - Jeśli port zajęty → fail z komunikatem „Port 8765 already in use. Kill process and retry."
  - `source .venv/bin/activate`
  - `exec uvicorn server:app --host ${WHISPER_HOST:-127.0.0.1} --port ${WHISPER_PORT:-8765}`

- [ ] `chmod +x start.sh`

**Warmup — timeout i error handling (D13 update):**
  - Warmup timeout: 30 sekund. Jeśli warmup() > 30s lub crash'uje:
    - Loguj warning
    - Service nie zawiesza się, lifespan kontynuuje
    - `/health` zwraca `200 { model_loaded: true, warmup_complete: false }`
    - Developer widzi że model loaded ale warmup failed
  - Warmup call: `numpy.zeros(32000)` przy 16 kHz = 2 sec silence, `vad_filter=False`

**Kryterium akceptacji:**
```
$ ./start.sh
{"ts":"2026-04-08T21:30:00Z","level":"INFO","msg":"Loading model large-v3 on cuda..."}
{"ts":"2026-04-08T21:30:03Z","level":"INFO","msg":"Model loaded","latency_ms":3421}
{"ts":"2026-04-08T21:30:04Z","level":"INFO","msg":"Warmup complete","latency_ms":1203}
INFO:     Uvicorn running on http://127.0.0.1:8765

# w innym terminalu:
# /ping dostępny ZARAZ (bez czekania na model)
$ curl -s http://localhost:8765/ping | jq
{
  "status": "ok"
}

# /health zwraca warmup_complete (true jeśli ready, false jeśli still warming)
$ curl -s http://localhost:8765/health | jq
{
  "model_loaded": true,
  "warmup_complete": true,
  "model_name": "large-v3",
  "device": "cuda",
  "compute_type": "int8_float16",
  "uptime_s": 12
}

# Każdy moduł <200 linii
# start.sh pre-checks port jest wolny
# Warmup timeout 30s zaimplementowany
$ wc -l server.py models.py transcribe.py logging_setup.py
  62 server.py
  38 models.py
  52 transcribe.py
  28 logging_setup.py
```

## Phase 3 — /transcribe endpoint

**Cel:** service transkrybuje przesłane audio, obsługuje błędy, timeout.

**Do zrobienia:**

- [ ] Pydantic models:
  - `TranscribeRequest` — `audio_base64: str` (required), `mime: str | None = None`, `language: str = "auto"`
  - `TranscribeResponse` — `text, language, language_probability (Optional[float]), duration_s, latency_ms, model`
  - `ErrorResponse` — `error: str, message: str, details: dict | None = None`
- [ ] Constant: `SUPPORTED_MIMES: set[str]` z `api_spec.md`
- [ ] `POST /transcribe` endpoint — **validation order is important:**
  - Jeśli `not app.state.model_loaded` → `503 model_not_loaded`
  - **Order of validation (fail-fast):**
    1. Pydantic validates: `audio_base64` present + is string (422 if missing/wrong type)
    2. MIME validate (if provided): spoza listy → `400 unsupported_mime`
    3. **PRE-CHECK base64 size** (BEFORE decode):
       ```python
       MAX_B64_SIZE = WHISPER_MAX_BYTES * 4 / 3  # ~33 MB (33% overhead)
       if len(audio_base64) > MAX_B64_SIZE:
           return 413 ErrorResponse(
               error="payload_too_large",
               message=f"Audio base64 too large (max {MAX_B64_SIZE} bytes)"
           )
       ```
       Rationale: Decoding huge base64 spikes memory. Fail fast.
    4. Decode base64 (try/except binascii.Error → `400 invalid_request`)
    5. Language code validation (if != "auto"):
       ```python
       ISO_639_1_CODES = {"pl", "en", "de", "fr", "es", ...}  # ~200 codes
       if language not in ISO_639_1_CODES and language != "auto":
           return 400 ErrorResponse(
               error="invalid_language",
               message=f"'{language}' is not a valid ISO 639-1 code"
           )
       ```
    6. Walidacja non-empty (`len(audio_bytes) > 0` → `400 invalid_request`)
    7. Walidacja rozmiaru decoded (`len(audio_bytes) <= WHISPER_MAX_BYTES` → `413 payload_too_large`)
  - Wrap transcribe call w `asyncio.wait_for()` z `WHISPER_REQUEST_TIMEOUT_S` (default 300s)
  - `_do_transcribe(audio_bytes, language)` — **sync method** (runs in executor thread):
    ```python
    def _do_transcribe(audio_bytes: bytes, language: str):
        """
        NOTE: model.transcribe() returns a lazy generator for segments.
        Without list() materialization, the model never runs (D17 gotcha).
        This is by design in faster-whisper.
        """
        bio = io.BytesIO(audio_bytes)
        segments, info = model.transcribe(
            bio,
            language=None if language == "auto" else language
        )
        # Materializuj generator — HERE inference actually runs
        segments_list = list(segments)
        
        text = " ".join(s.text.strip() for s in segments_list).strip()
        duration = info.duration
        
        # Handle language detection:
        # - If requested lang was "auto": model detected, return probability
        # - If requested lang was explicit: return None (no detection done)
        # - If audio was silent: info.language is None, return "unknown"
        if info.language is None:
            lang = "unknown"  # Silent audio, model couldn't detect
            lang_prob = None
        elif language != "auto":
            lang = info.language
            lang_prob = None  # Explicit language, no detection
        else:
            lang = info.language
            lang_prob = info.language_probability  # Auto-detect result
        
        return {
            "text": text,
            "language": lang,
            "language_probability": lang_prob,
            "duration_s": round(duration, 2),
            "latency_ms": latency,
            "model": MODEL_NAME,
        }
    ```
  - Zmierz `latency_ms` (tylko sam `list(segments)` + transcribe, bez base64 decode)
  - Zwróć `TranscribeResponse`
  - Error handling: timeout → `504`, model crash → `500`, inne → `500`

**Kryterium akceptacji:**
```
$ AUDIO_B64=$(base64 -w0 < fixtures/pl_chrzaszcz.ogg)
$ curl -s -X POST http://localhost:8765/transcribe \
    -H "Content-Type: application/json" \
    -d "{\"audio_base64\":\"$AUDIO_B64\",\"language\":\"pl\"}" | jq
{
  "text": "W Szczebrzeszynie chrząszcz brzmi w trzcinie...",
  "language": "pl",
  "language_probability": null,
  "duration_s": 9.21,
  "latency_ms": 420,
  "model": "large-v3"
}
```

Plus error cases działają:
- Brak `audio_base64` → 422
- Garbage base64 → 400 `invalid_request`
- `mime: image/png` → 400 `unsupported_mime`
- Base64 > 33 MB (pre-check) → 413 `payload_too_large`
- Audio (decoded) > 25 MB → 413 `payload_too_large`
- `language: "klingon"` → 400 `invalid_language`
- Empty audio bytes → 400 `invalid_request`

Jeśli audio jest całkowicie silent (language detection fails):
- Zwróć `language: "unknown"`, `language_probability: null`

## Phase 4 — pytest integration tests

**Cel:** `pytest tests/` przechodzi, wszystkie kluczowe ścieżki pokryte.

**Do zrobienia:**

- [ ] Stwórz `tests/conftest.py`:
  ```python
  from pathlib import Path
  import pytest
  from fastapi.testclient import TestClient
  from server import app

  @pytest.fixture(scope="session")
  def client():
      with TestClient(app) as c:  # triggers lifespan
          yield c

  @pytest.fixture(scope="session")
  def fixtures_dir():
      return Path(__file__).parent.parent / "fixtures"

  @pytest.fixture
  def pl_sample(fixtures_dir):
      return (fixtures_dir / "pl_chrzaszcz.ogg").read_bytes()

  @pytest.fixture
  def en_sample(fixtures_dir):
      return (fixtures_dir / "en_fox.ogg").read_bytes()

  @pytest.fixture
  def long_silence_audio():
      """Generate 6 min of silence for timeout testing (5,760,000 samples at 16kHz)"""
      import numpy as np
      import soundfile
      import io
      samples = np.zeros(5_760_000, dtype=np.float32)
      bio = io.BytesIO()
      soundfile.write(bio, samples, 16000, format='WAV')
      return bio.getvalue()
  ```
- [ ] Stwórz `tests/test_health.py`:
  - `test_health_returns_200_with_model_loaded(client)`
  - `test_health_has_expected_fields(client)` — sprawdza `model_loaded`,
    `warmup_complete`, `model_name`, `device`, `compute_type`, `uptime_s`
  - `test_health_warmup_complete_is_bool(client)` — `warmup_complete` to boolean (true/false)
  - `test_health_has_no_status_field(client)` — regression test dla D14 cut
- [ ] Stwórz `tests/test_transcribe.py`:
  - **Happy path:**
    - `test_transcribe_pl_sample(client, pl_sample)` — sprawdza że text
      zawiera „Szczebrzeszynie" (case-insensitive substring)
    - `test_transcribe_en_sample(client, en_sample)` — sprawdza że text
      zawiera „brown fox"
    - `test_transcribe_auto_detect(client, pl_sample)` — bez language, sprawdza
      że `language == "pl"` i `language_probability` is not None
    - `test_transcribe_forced_language_returns_null_probability(client, pl_sample)`
      — sprawdza że `language_probability is None` gdy `language="pl"`
  - **Error cases:**
    - `test_missing_audio_base64_returns_422(client)` — brak pola
    - `test_invalid_base64_returns_400(client)` — garbage base64
    - `test_unsupported_mime_returns_400(client)` — `mime: "image/png"`
    - `test_base64_too_large_returns_413(client)` — base64 > 33 MB (pre-check)
    - `test_oversized_payload_returns_413(client)` — decoded audio > WHISPER_MAX_BYTES
    - `test_empty_audio_returns_400(client)` — 0 bytes
    - `test_invalid_language_code_returns_400(client)` — `language="klingon"` (not ISO 639-1)
    - `test_transcribe_timeout_returns_504(client, long_silence_audio)` — 6 min silence audio, trigger 300s timeout
    - `test_concurrent_requests_serialize(client, pl_sample, en_sample)` — dwa requesty równocześnie, sprawdz że oba succeed (serialnie, drugi czeka)
  - **Case sensitivity (important!):**
    - `test_transcribe_case_insensitive(client, pl_sample)` — assert `.lower()` na tekście przed compare
    - Whisper może zwrócić "SZCZEBRZESZYNIE" lub "szczebrzeszynie" — sprawdź `.lower()` zawiera target
  - **Additional fixtures** (opcjonalne ale zalecane — see
    `fixtures/README.md` dla coverage matrix i test purposes):
    - `pl_alphabet.ogg` — diacritics stress (`ą ę ć ł ń ó ś ź ż`)
    - `pl_smartfon.ogg` — long-form PL (~40s), assertion: startswith
      "Smartfon" + contains "telefonu komórkowego"
    - `en_uk_north_wind.ogg` — long-form UK English (~36s), exact-match
      possible (IPA canonical text)
    - `en_us_election.ogg` — US English + legal/proper-noun vocab

**Kryterium akceptacji:**
```
$ source .venv/bin/activate
$ pip install -r requirements-dev.txt
$ pytest tests/ -v  # unit + basic integration tests
tests/test_health.py::test_health_returns_200_with_model_loaded PASSED
tests/test_health.py::test_health_has_expected_fields PASSED
tests/test_health.py::test_health_has_no_status_field PASSED
tests/test_transcribe.py::test_transcribe_pl_sample PASSED
tests/test_transcribe.py::test_invalid_base64_returns_400 PASSED
tests/test_transcribe.py::test_invalid_language_code_returns_400 PASSED
tests/test_transcribe.py::test_concurrent_requests_serialize PASSED
... (wszystkie bez timeout test PASSED)
============ N passed in ~30s ============

# Timeout test jest SLOW (300s+), skip by default:
$ pytest tests/ -v -m "not slow"   # bez timeout test
$ pytest tests/ -v -m slow         # TYLKO timeout test (5+ minut)
```

## Phase 5 — Logging + polish

**Cel:** service loguje każdy request w JSON lines, kod jest czysty.
Modularization już zrobiona w Phase 2 (D16).

**Do zrobienia:**

- [ ] Expand `logging_setup.py` (from Phase 2 skeleton):
  - `JSONFormatter` — custom (D17, no external deps)
  - Format: `{"ts": ISO8601, "level": ..., "msg": ..., ...extra}`
  - Handler: `StreamHandler(sys.stdout)` (nie file — user kontroluje rotation z `tee`)
  - Level z `WHISPER_LOG_LEVEL` env var
  - Test: `logging.basicConfig(level=...)` works

- [ ] Add logging calls throughout:
  - `server.py`:
    - Startup: `{"ts": "...", "level": "INFO", "msg": "Whisper service starting", "device": "cuda"}`
    - Ready: `{"ts": "...", "level": "INFO", "msg": "Whisper service ready", "model": "large-v3"}`
    - Shutdown: `{"ts": "...", "level": "INFO", "msg": "Whisper service shutting down"}`
  
  - `transcribe.py` — `/transcribe` request logging:
    ```python
    # In /transcribe route (FastAPI):
    from uuid import uuid4
    request_id = uuid4().hex[:12]
    logger.info("transcribe_start", extra={
        "request_id": request_id,
        "audio_bytes": len(audio_bytes),
        "language_requested": language
    })
    
    # In _do_transcribe (executor thread):
    # request_id is captured via closure
    start_time = time.time()
    ... transcribe logic ...
    latency_ms = int((time.time() - start_time) * 1000)
    logger.info("transcribe_complete", extra={
        "request_id": request_id,
        "latency_ms": latency_ms,
        "language_detected": detected_language,
        "duration_s": duration_s
    })
    ```
    
    Rationale: request_id helps correlate start/complete logs even in
    single-threaded service (debugging "which request caused hang?")
  
  - `models.py` — none (schemas are pure data)

- [ ] Code polish (all modules already modularized):
  - Type hints na publicznych functions/methods (już w Phase 2)
  - Docstrings (krótkie, tylko gdzie non-obvious)
  - ✓ Każdy plik < 200 linii (zrobione w Phase 2 D16)
  - `mypy` type check (opcjonalne, nice-to-have)

**Kryterium akceptacji:**
```
$ ./start.sh 2>&1 | head
{"ts": "2026-04-08T20:00:00Z", "level": "INFO", "msg": "Loading model large-v3 on cuda..."}
{"ts": "2026-04-08T20:00:03Z", "level": "INFO", "msg": "Model loaded", "latency_ms": 3421}
{"ts": "2026-04-08T20:00:04Z", "level": "INFO", "msg": "Warmup complete", "latency_ms": 1203}
{"ts": "2026-04-08T20:00:05Z", "level": "INFO", "msg": "Whisper service ready", "model": "large-v3"}

# w drugim terminalu, po curl POST /transcribe:
$ ./start.sh 2>&1 | grep transcribe
{"ts": "2026-04-08T20:00:42Z", "level": "INFO", "msg": "transcribe_start", "request_id": "a1b2c3d4e5f6", "audio_bytes": 88517, "language_requested": "pl"}
{"ts": "2026-04-08T20:00:43Z", "level": "INFO", "msg": "transcribe_complete", "request_id": "a1b2c3d4e5f6", "latency_ms": 420, "language_detected": "pl", "duration_s": 9.21}
```

## Phase 6 — Dokumentacja

**Cel:** `README.md` w root service, `CLAUDE.md` zaktualizowany po
realizacji, wpis w root `CLAUDE.md` repo wskazujący na service.

**Do zrobienia:**

- [ ] Stwórz `services/whisper/README.md`:
  - **Co to jest** (1 paragraph) — local HTTP microservice for STT
  - **Wymagania:**
    - Python 3.10+
    - CUDA + cuDNN (optional, fallback to CPU if missing, ~5-10× slower)
    - 8 GB VRAM (fits `large-v3` int8)
  - **Quick start:**
    ```bash
    ./setup.sh      # Install deps, download model (~3 GB)
    ./start.sh      # Start service on http://127.0.0.1:8765
    curl http://localhost:8765/health  # Verify
    ```
  - **API summary** (link do `PLAN/api_spec.md` + inline examples):
    - `GET /health` → `{"model_loaded": true, ...}`
    - `POST /transcribe` (audio_base64 + language) → `{"text": "...", ...}`
  - **Environment variables** (table from `api_spec.md`)
  - **Troubleshooting:**

    | Problem | Symptom | Solution |
    |---|---|---|
    | CUDA not found | Logs show `device: "cpu"`, slow (30s+/minute audio) | Install NVIDIA driver + cuDNN. Or accept CPU. |
    | cuDNN missing | `libcudnn.so.8: cannot open shared object file` | `sudo apt install libcudnn9` (Ubuntu). Set `LD_LIBRARY_PATH` if custom install. |
    | VRAM OOM | `CUDA out of memory` error during warmup | Fallback: `WHISPER_MODEL=large-v3-turbo ./start.sh` (saves ~1 GB, -2-5% quality). |
    | Port busy | `Address already in use :8765` from uvicorn | `lsof -i :8765` find process, `kill PID`, then restart. |
    | Model download hangs | `setup.sh` stuck at model download | Use HF mirror: `HF_ENDPOINT=https://huggingface.co ./setup.sh`. Check internet. |
    | Model validation fails | `validate_model.py` → "Model not found" | Re-run `./setup.sh` from scratch. |
    | Service won't start | `./start.sh` → import error (no module) | `source .venv/bin/activate` manually, `pip install -r requirements.txt`. |
    | Request hangs | POST to `/transcribe` gets no response after 5 min | Server timeout (default 300s = 5 min). Kill and restart. |
    | Language detection wrong | Transcribe with `language="auto"`, wrong language detected | Force language: `{"language": "pl"}` in request. |
- [ ] Zaktualizuj `services/whisper/CLAUDE.md`:
  - Zmień `STATUS: PLANOWANE, NIE ZBUDOWANE` na `STATUS: ZBUDOWANY, DZIAŁAJĄCY`
  - Update "Co to jest" — krótko, że service jest gotowy
  - Zachowaj operational rules:
    - **Nigdy** nie odpalaj `start.sh` w tle bez wyraźnej zgody (persistent VRAM)
    - **Nigdy** nie bindiuj na `0.0.0.0` (localhost only)
    - **Nigdy** nie commituj `.env` ani `.venv/`
    - **Nigdy** nie modyfikuj `fixtures/` (CC BY-SA attribution)
  - Fallback chain when VRAM issues:
    - Sprawdź `nvidia-smi` czy GPU faktycznie wolny
    - Jeśli GPU wolny ale OOM: `WHISPER_MODEL=large-v3-turbo ./start.sh` (fallback)
    - Jeśli dalej OOM: fallback na CPU (`WHISPER_DEVICE=cpu`)
  - Zachowaj directive „Don't flatter, be critical"
  - Add section "Czy service jest uruchomiony?" z health check command

- [ ] Zaktualizuj root `/home/leto/Arts/aidevs4/CLAUDE.md`:
  - Dodaj sekcję w Architecture section, wskazując na `services/whisper/`:
    ```
    ## services/whisper — Local STT (Speech-to-Text)
    
    HTTP microservice na `127.0.0.1:8765`. Przyjmuje audio (base64 JSON),
    zwraca transkrypcję. Lokalnie — bez kosztów OpenAI API.
    
    Setup: `cd services/whisper && ./setup.sh && ./start.sh`
    Health check: `curl http://127.0.0.1:8765/health`
    
    Szczegóły: [services/whisper/README.md](./services/whisper/README.md)
    ```
  - Dodaj do Common patterns section informację że service może być użyty
    z dowolnego `tasks/*` projektu

- [ ] Dodaj sekcję "Performance expectations" do README.md:
  ```markdown
  ## Performance
  
  - **CUDA (RTX 4090 equivalent):** ~200-400 ms/minute of audio (10-30× realtime)
  - **CUDA (older GPU, e.g., RTX 2070):** ~1-2 s/minute of audio
  - **CPU:** ~5-10 s/minute of audio
  - **Startup:** ~5 min (model download+warmup on first run), ~3 min (warmup on restart)
  - **Per-request latency:** Includes transcription time only, not base64 decode
  - **Request timeout:** 300 seconds (5 minutes). On CPU, audio >5 min may timeout.
    For longer audio, either use GPU or increase `WHISPER_REQUEST_TIMEOUT_S` env var.
  - **Concurrent requests:** Sequential (ThreadPoolExecutor max_workers=1).
    Second request waits for first to complete.
  ```

- [ ] Dodaj "Known limitations" section:
  ```markdown
  ## Known Limitations
  
  - **Sequential transcription:** Only one audio processed at a time
    (ThreadPoolExecutor max_workers=1). Second request waits for first.
  - **No mid-request cancellation:** If service hangs, kill with `pkill -f "uvicorn server"`
  - **Model restart required:** Changing model requires service restart
  - **No authentication:** Localhost only (OS trust boundary)
  ```

**Kryterium akceptacji:**
Świeża sesja Claude Code uruchomiona w `services/whisper/` od razu wie
jak debugować problemy (po przeczytaniu `CLAUDE.md` + `README.md`). Świeża
sesja w dowolnym `tasks/*` widzi w root `CLAUDE.md` że whisper jest
dostępny lokalnie. README ma Troubleshooting table + Performance expectations.

---

## Anti-cele (wyraźnie POMIJAMY)

- Autoryzacja / API keys
- Docker / kontener
- Streaming transcription
- Speaker diarization
- Multi-model hot swap (w runtime)
- Prometheus metrics
- `/models` endpoint (wycięty — klient nie potrzebuje)
- `vram_used_mb` / `transcriptions_total` w `/health` (wycięte — minimal
  surface area)
- `status` field w `/health` (HTTP status code niesie tę info)
- Distributed deployment
- Systemd user unit (może być dodany później jako opt-in, poza zakresem)

Trzymaj się zakresu. Jeśli pojawi się pokusa dodania czegoś spoza listy —
zapisz w „Future work" sekcji README i skończ main work.
