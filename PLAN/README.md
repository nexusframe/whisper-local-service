# services/whisper — Plan implementacji

Lokalny HTTP microservice do transkrypcji audio, oparty o
[`faster-whisper`](https://github.com/SYSTRAN/faster-whisper)
(CTranslate2 backend). Przyjmuje audio (base64 w JSON POST),
zwraca tekst. Całość chodzi lokalnie, model w VRAM, brak połączeń
z zewnętrznymi API.

## Why this exists

1. **Local STT provider pattern** — alternatywa dla OpenAI Whisper API,
   demonstracja jak self-hosted model wpina się w ten sam interface co
   cloud provider.
2. **GPU utilization** — 8 GB VRAM jest dostępne, whisper mieści się,
   zero kosztu marginalnego per transkrypcja.
3. **Privacy** — audio nigdy nie opuszcza maszyny.

## Quick facts

- **Stack:** Python 3.10+, FastAPI, uvicorn, faster-whisper (CTranslate2)
- **Model:** `large-v3` int8 (fallback do `large-v3-turbo` int8 gdy VRAM pressure)
- **Host:** `127.0.0.1:8765` (localhost only, żadnego external bind)
- **VRAM budget:** 8 GB (ograniczenie sprzętowe właściciela)
- **Concurrency:** sekwencyjne przetwarzanie przez `ThreadPoolExecutor(max_workers=1)`
- **Uruchamianie:** manualnie przez `./start.sh`, bez systemd

## Alternatywy rozważone (i odrzucone)

| Opcja | Powód odrzucenia |
|---|---|
| Python subprocess per call | Cold start ~3-5s × N calls = wasted CUDA warmup |
| Long-running subprocess z stdin/stdout pipe | Process management w kliencie, single-tenant, nie reusable |
| Python library embedded w kliencie | Wymusza Python w każdym kliencie, łamie language-agnostic |
| MCP server | MCP to protokół agent↔tool głównie stdio, over-engineered dla persistent service |
| **HTTP service** ⭐ | Model raz w VRAM, multi-client, debuggable przez curl, language-agnostic |

Szczegółowe uzasadnienie → [`decisions.md`](./decisions.md) D0.

## Dla nowej sesji — od czego zacząć

1. Przeczytaj ten plik — kontekst i szybkie fakty (masz właśnie tu jesteś)
2. Przeczytaj [`decisions.md`](./decisions.md) — wszystkie decyzje projektowe
   są już podjęte, z uzasadnieniem i odrzuconymi alternatywami
3. Przeczytaj [`api_spec.md`](./api_spec.md) — dokładny kontrakt HTTP API
   (endpointy, request/response, błędy)
4. Wykonuj [`phases.md`](./phases.md) fazami — każda z wyraźnym kryterium
   akceptacji, 6 faz od fundamentu do dokumentacji

## Pliki w tym katalogu

- [`README.md`](./README.md) — ten plik (scope, rationale, index)
- [`decisions.md`](./decisions.md) — log decyzji projektowych (D0-D15)
- [`api_spec.md`](./api_spec.md) — HTTP API contract
- [`phases.md`](./phases.md) — fazy implementacji z checkboxami

## Success criteria

Service jest gotowy gdy:

1. `./setup.sh` uruchomiony na czystej maszynie (Python 3.10+) kończy się sukcesem
2. `./start.sh` uruchamia uvicorn, model ładuje się bez błędów, warmup call
   wykonany
3. `GET /health` zwraca `200` + `{"model_loaded": true, "device": "cuda", ...}`
4. `POST /transcribe` z fixture `fixtures/pl_chrzaszcz.ogg` zwraca poprawną
   polską transkrypcję zawierającą „Szczebrzeszynie"
5. `pytest tests/` przechodzi wszystkie testy
6. `README.md` i `CLAUDE.md` (w root service) wyjaśniają jak uruchomić
   i debuggować
