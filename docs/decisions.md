# Decisions — services/whisper

Log decyzji projektowych. Każda decyzja ma uzasadnienie i odrzucone
alternatywy — jeśli napotkasz edge case, wróć do „why" żeby zdecydować
zgodnie z duchem.

## D0: HTTP service (nad subprocess / library / MCP)

**Wybór:** Long-running HTTP service (FastAPI + uvicorn), localhost only.

**Dlaczego:**
- Model raz załadowany w VRAM, multi-client bez cold start per-call
- Debuggable przez curl / przeglądarkę bez setupu klienta
- Language-agnostic klienci (Python, Node.js, shell, cokolwiek co robi HTTP)
- Analogia do OpenAI API — łatwa migracja w obie strony (local ↔ cloud)
- Localhost trust boundary = brak auth overhead

**Odrzucone:**
- **Python subprocess per call** — cold start ~3-5s × N calls = wasted CUDA
  warmup. Marnotrawstwo przy więcej niż jednym wywołaniu.
- **Long-running subprocess z stdin/stdout pipe** — model ładowany raz, ale
  zarządzanie procesem w kliencie jest upierdliwe, single-tenant, nie reusable
  między klientami.
- **Python library embedded w kliencie** — wymusza Python w każdym kliencie,
  łamie zasadę language-agnostic API.
- **MCP server** — MCP to protokół agent↔tool, głównie stdio. Jako persistent
  service = over-engineered. Jeśli kiedyś trzeba MCP — tanki adapter nad HTTP.

## D1: Framework — FastAPI + uvicorn

**Wybór:** FastAPI + uvicorn

**Dlaczego:**
- Standardowy wzorzec w ekosystemie Python dla HTTP API
- Pydantic validation za darmo (walidacja request JSON bez ręcznego kodu)
- Swagger UI na `/docs` za darmo (łatwy debug przez przeglądarkę)
- Async support (w razie potrzeby) — nieużywany na razie, ale jest pod ręką
- Minimalna ilość boilerplate'u (dekoratory jak Flask, typowanie jak Spring)

**Odrzucone:**
- `http.server` stdlib — prosty, ale walidacja ręczna, brak swagger, brak pydantic
- Flask — wymaga marshmallow albo ręcznej walidacji
- Django — overkill, ORM niepotrzebny

## D2: Biblioteka Whisper — faster-whisper

**Wybór:** `faster-whisper` (CTranslate2 backend)

**Dlaczego:**
- Reimplementation w CTranslate2 → 4× szybszy od oryginalnego `openai-whisper`
- Wsparcie quantization (int8, int8_float16, float16) → mieści się w 8 GB VRAM
- Aktywnie utrzymywany, popularny w community
- Wspiera forced language, VAD, timestamps
- Pod spodem używa `av` (PyAV) z bundlowanym ffmpeg — bez system ffmpeg dep

**Odrzucone:**
- `openai-whisper` (oryginał) — wolniejszy, fp16 `large-v3` nie mieści się w 8 GB
- `whisper.cpp` — świetny, ale nie ma Python bindings (tylko C++ albo CLI),
  trudniej zintegrować z FastAPI
- `whisperX` — dobre do diarization, ale anti-goal „no speaker diarization"

## D3: Model domyślny — large-v3 int8

**Wybór:** `large-v3` z quantization `int8` (lub `int8_float16` gdy GPU
wspiera compute capability ≥7.0, obsługiwane przez `compute_type='auto'`).

**Dlaczego:**
- `large-v3` = flagowy model Whisper, najlepsza jakość dla szerokiej gamy języków
- Quantization int8 → ~3 GB VRAM (weights ~1.5 GB + activations),
  bezpiecznie mieści się w 8 GB
- Najlepsza jakość dla polskiego i noisy audio (nasza main use case)
- Na GPU 10-30× realtime

**Dlaczego NIE `large-v3-turbo`:**
- Turbo jest ~2× szybsze ale traci ~2-5% WER
- W 8 GB VRAM mamy miejsce na pełny large-v3 — nie ma realnego powodu dla
  kompromisu jakościowego
- Turbo pozostaje jako **fallback** gdy VRAM pressure (→ CLAUDE.md)

**Odrzucone:**
- `large-v3` fp16 — ~10 GB VRAM, NIE mieści się
- `large-v3-turbo` int8 — niższa jakość bez realnego zysku VRAM w naszym env
- `medium` int8 — zauważalnie gorszy dla polskiego
- `small` — za słaby dla produkcji

**Konfiguracja przez env vars:**
- `WHISPER_MODEL` (default `large-v3`)
- `WHISPER_COMPUTE_TYPE` (default `auto` — faster-whisper sam wybiera int8 lub int8_float16)
- `WHISPER_DEVICE` (default `auto` — cuda jeśli dostępne, inaczej cpu)

## D4: Port i bind address

**Wybór:** `127.0.0.1:8765`

**Dlaczego:**
- `127.0.0.1` (nie `0.0.0.0`) → tylko localhost, żadnego dostępu z sieci.
  Brak zagrożenia z LAN/internetu.
- Port `8765` — niekolidujący z typowymi portami (Jupyter 8888, Vite 5173,
  FastAPI defaults 8000)
- Konfigurowalny przez `WHISPER_PORT` env var

**Odrzucone:**
- `0.0.0.0` — otwieranie na cały świat bez autoryzacji = security hole
- `8000` — kolizja z innymi FastAPI projektami

## D5: Format inputu — JSON z base64

**Wybór:** `POST /transcribe` z JSON body zawierającym `audio_base64` (string)

**Dlaczego:**
- Prosty do wygenerowania z dowolnego języka (`Buffer.from(buf).toString('base64')`
  w Node, `base64.b64encode()` w Python)
- Nie wymaga multipart/form-data (więcej kodu po obu stronach)
- Pydantic waliduje za darmo
- Łatwe do zalogowania w trace.log (JSON serializable)

**Koszt:**
- Base64 zwiększa rozmiar payloadu o ~33% — akceptowalne dla local HTTP
- Dla audio >10 MB warto rozważyć multipart — na razie non-goal

**Limit rozmiaru:** 25 MB (zgodne z OpenAI Whisper API, łatwa migracja).
Konfigurowalne przez `WHISPER_MAX_BYTES`.

**`mime` field:** optional. faster-whisper/ffmpeg sniffuje format z magic
bytes niezależnie od tego co klient deklaruje — wymaganie `mime` byłoby
placebo. Opcjonalne dla lepszych komunikatów błędów.

## D6: Pre-download modelu w setup.sh

**Wybór:** `setup.sh` pobiera model z HuggingFace przy pierwszym uruchomieniu.
Serwer uruchamiany przez `start.sh` zakłada że model już jest lokalnie.

**Dlaczego:**
- Deterministic — wiadomo kiedy idzie pobieranie ~3 GB
- Lazy load przy pierwszym request byłby mylący (pierwszy call trwa minuty)
- Separation of concerns: `setup.sh` = one-time install, `start.sh` = daily use

**Cache location:** default HuggingFace (`~/.cache/huggingface/`). Nie
nadpisujemy — shared cache między projektami oszczędza dysk.

**Odrzucone:**
- Lazy load przy starcie servera — długi cold start, mylący użytkownika
- Custom cache path w projekcie — duplikuje download jeśli user ma inne
  projekty używające tego samego modelu

## D7: Jeden model załadowany na raz

**Wybór:** Service ładuje JEDEN model przy starcie. Przełączanie modeli
wymaga restart.

**Dlaczego:**
- 8 GB VRAM = miejsce na jeden `large-v3` int8
- Ładowanie multiple = OOM risk
- Prostota implementacji — zero logiki hot-swap

**Konsekwencje:**
- User który chce inny model → zmienia `WHISPER_MODEL` env var i restartuje
- `GET /models` endpoint nie istnieje (cut w scope Alt B — klient nie potrzebuje)

## D8: Sekwencyjne przetwarzanie przez ThreadPoolExecutor(max_workers=1)

**Wybór:** `asyncio.run_in_executor()` z `ThreadPoolExecutor(max_workers=1)`.
Pojedynczy worker thread automatycznie serializuje transcribe calls.

**Dlaczego:**
- `faster_whisper.WhisperModel.transcribe()` jest **blocking sync call** —
  NIE async. Trzymanie `asyncio.Lock` wokół sync call zablokowałoby CAŁY
  event loop FastAPI (łącznie z `/health`). To było błędem w oryginalnym
  projekcie.
- Single-worker executor = serializacja bez explicit lock, event loop
  wolny dla `/health` i innych endpointów podczas długiego transcribe
- Whisper na GPU nie skaluje dobrze batchingiem dla krótkich audio

**Implementacja:**
```python
# w lifespan
app.state.executor = ThreadPoolExecutor(max_workers=1)
yield
app.state.executor.shutdown(wait=True)

# w /transcribe
loop = asyncio.get_event_loop()
result = await asyncio.wait_for(
    loop.run_in_executor(app.state.executor, _do_transcribe, audio_bytes, lang),
    timeout=300  # 5 min hard cap
)
```

**Znana ograniczenie:** `asyncio.wait_for` z timeout anulluje co-routine,
ale NIE kill'uje executor threada. Długi transcribe dalej liczy, następny
request czeka. Akceptowalne dla dev-only use case.

**Odrzucone:**
- `asyncio.Lock` — bug: blokuje event loop, bo transcribe jest sync
- `threading.Lock` + default executor — działa ale nie-explicit, łatwo zepsuć
- Kolejka z priorytetami / multi-worker — over-engineered, 8 GB VRAM nie
  utrzyma dwóch modeli naraz

## D9: Language default = auto, klient może wymusić

**Wybór:** Domyślnie `language=auto` (model wykrywa). Klient może wymusić
`language="pl"` dla znanych języków.

**Dlaczego:**
- Auto-detect jest solidny w `large-v3`
- Klient który wie co wysyła → wymuszenie jest szybsze i dokładniejsze
- Elastyczne dla klientów z nieznanym językiem

**`language_probability` field:** `null` gdy język wymuszony (model pomija
detection), float 0.0-1.0 gdy auto-detect. NIE zwracamy sztucznego `1.0`
dla wymuszonego bo to semantyczne kłamstwo.

## D10: Uruchamianie — manualne przez `./start.sh`

**Wybór:** User uruchamia `./start.sh` ręcznie przed użyciem. Brak
systemd/autostart.

**Dlaczego:**
- Prostota — zero systemd knowledge wymagane
- Developer-centric workflow — service odpalany tylko gdy potrzebny
- Persistent service zajmuje VRAM, nie chcemy go trzymać stale

**Konsekwencje:**
- Klient MUSI sprawdzić `/health` na starcie i fail-fast z jasnym komunikatem
  jeśli service nie odpowiada: `"Whisper service not running. Start: cd
  services/whisper && ./start.sh"`
- `start.sh` pre-checkuje czy port 8765 wolny (przez `lsof` lub `ss`) żeby
  fail-fast zamiast cryptic BindError po 10s model loadingu

## D11: Bez autoryzacji

**Wybór:** Brak auth, brak tokenów. Localhost only = trust boundary to
system operacyjny.

**Dlaczego:**
- Localhost bind = tylko procesy na tej maszynie mają dostęp
- Dodanie tokenów to complexity bez realnego zysku w tym use case
- Jeśli service kiedykolwiek miałby wyjść poza localhost → wtedy dodamy auth

**Known risk:** lokalne procesy userspace (browser extensions, dev tools)
teoretycznie mogą trafić na `/transcribe`. Dla single-user dev machine
akceptowalne. Gdyby service kiedyś hostował shared machine → dodać token.

## D12: Folder w repo (nie submodule)

**Wybór:** `services/whisper/` jako zwykły folder.

**Dlaczego:**
- Łatwy dostęp z dowolnego projektu w tym repo
- Jedna historia git
- Jeśli kiedyś inny projekt będzie chciał ten service → wtedy można wyekstrahować

## D13: Model warmup po load

**Wybór:** Po załadowaniu modelu w `lifespan` wykonaj jedno „warmup"
wywołanie na 2 sekundach ciszy (`numpy.zeros(32000, dtype=np.float32)`
przy 16 kHz sample rate). `vad_filter=False` żeby model rzeczywiście
przejechał przez pełny pipeline (VAD by odrzucił ciszę). **Warmup robi timeout 30s.**

**Dlaczego:**
- Model loaded ≠ model warm. Pierwsza real transkrypcja po load jest
  2-3× wolniejsza (kernel compilation, CUDA graph, buffer allocation).
- Warmup przeniesie tę latency do fazy startup, gdzie nie blokuje klienta
- `/health` powinien zwracać `200` + `model_loaded: true, warmup_complete: true` dopiero PO warmupie

**Warmup error handling:**
- Jeśli warmup() timeout'uje (>30s) lub crash'uje:
  - Loguj warning (JSON log z stack trace)
  - Service start się **nie zawiesza**, kontynuuje
  - `/health` zwraca `200 { model_loaded: true, warmup_complete: false }`
  - Developer widzi że model jest ale warmup failed, może debugować
  - Pierwszy `/transcribe` request będzie powolny (bez warmupu), ale będzie działać

**Alternatywa (odrzucona):**
- Failnąć startup jeśli warmup się wali — za surowe, debugowanie trudniejsze

## D14: Logging — JSON lines na stdout

**Wybór:** Structured logs w formacie JSON lines (`{"ts":...,"level":...,"msg":...}`),
wypisywane na stdout. Service nie zarządza plikami logów.

**Dlaczego:**
- Unix way — stdout jest domeną procesu, redirection domeną usera
- JSON lines łatwe do parsowania (jq, Langfuse, dowolny log collector)
- Zero file rotation / permission / cleanup complexity w service
- User może: `./start.sh 2>&1 | tee whisper.log` jeśli chce plik

**Odrzucone:**
- Plain text logs — trudniejsze do parsowania
- RotatingFileHandler — over-engineering dla dev-service
- Multiple log destinations — complexity bez benefitu

## D15: Fixtures w repo, not downloaded on setup

**Wybór:** Test fixture files (`fixtures/*.ogg`) są committed do repo.
`setup.sh` ich NIE pobiera.

**Dlaczego:**
- Total size ~215 KB — negligible git bloat
- Offline setup działa bez problemu
- Reproducibility — Wikimedia URL-e mogą się zmienić w latach
- Zero network IO w CI / setup

**Odrzucone:**
- Download w setup.sh — niepotrzebna zależność od internetu + fail mode
- Generowanie syntetycznego audio — nie masz known-good transkrypcji

## D16: Modularyzacja — Phase 2 struktura

**Wybór:** `server.py` rozbij na moduły od razu w Phase 2:
- `server.py` (~60 linii) — FastAPI routes only
- `models.py` (~40 linii) — Pydantic schemas (Request, Response, Error)
- `transcribe.py` (~50 linii) — WhisperExecutor class + sync logic
- `logging_setup.py` (~30 linii) — JSON logging configuration

**Dlaczego:**
- Trzyma każdy plik < 200 linii (root CLAUDE.md rule)
- Separation of concerns: schemas ≠ logic ≠ routes
- Łatwiej testować (mock `WhisperExecutor`, nie całą app)
- Phase 5 „code polish" nie wymaga refactoringu

**Alternatywa (odrzucona):**
- Monolith `server.py` 250+ linii → Phase 5 refactor → złe dla learnings
- Zamiast tego: design na modularność od start

## D17: JSON logging — custom formatter (bez external lib)

**Wybór:** JSON logging via `logging.Formatter` custom bez `python-json-logger` dep.

**Dlaczego:**
- Zmniejsza dependencies (3 biblioteki vs 4)
- Logging moduł jest builtin
- Formatter to ~30 linii prostego kodu
- Format: `{"ts": ISO8601, "level": ..., "msg": ..., ...extra}`

**Implementacja (D17 helper):**
```python
# logging_setup.py
import json
import logging
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_data["exc"] = self.formatException(record.exc_info)
        # Extra fields (logger.info("msg", extra={"key": "val"}))
        for key, val in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", etc.]:
                log_data[key] = val
        return json.dumps(log_data)
```

**Odrzucone:**
- `python-json-logger` — external dep bez real benefit dla dev service
