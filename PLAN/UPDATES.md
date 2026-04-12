# 📋 PODSUMOWANIE ZMIAN W PLANIE

## Post Symulowany Brainstorm Team'u + User Decision
 
Drużyna znalazła 15 flag'ów (3 HIGH, 12 MEDIUM/LOW). User podjął decyzje na 3 kluczowych pytaniach.
Zaaplikowano 5 konkretnych patch'ów do PLAN/.

## Zmiany w decyzjach (decisions.md)

### ⭐ D16: Modularyzacja — Phase 2 struktura
- `server.py` (~60 linii) — FastAPI routes only
- `models.py` (~40 linii) — Pydantic schemas
- `transcribe.py` (~50 linii) — WhisperExecutor + sync logic
- `logging_setup.py` (~30 linii) — JSON logging
- **Dlaczego:** Każdy plik < 200 linii (root CLAUDE.md rule), separation of concerns

### ⭐ D17: JSON logging — custom formatter
- No external deps (`python-json-logger`)
- Custom `JSONFormatter` w `logging_setup.py`
- Stdout only (user kontroluje rotation z `tee`)
- Format: `{"ts": ISO8601, "level": ..., "msg": ...}`

---

## Zmiany w fazach (phases.md)

### Phase 1 — Fundament
**Dodane:**
- CUDA check w setup.sh (detect GPU, warn if missing)
- `validate_model.py` — pre-flight model cache check
- Acceptance test pokazuje validate_model.py call

**Dlaczego:** Szybka feedback pre-start, model corruption detection

### Phase 2 — Scaffold FastAPI
**Restrukturyzacja (D16):**
- 4 pliki zamiast monolith `server.py`
- Każdy plik ze swoją odpowiedzialnością
- Acceptance test sprawdza wc -l (każdy < 200)

**Nowe:**
- `start.sh` pre-check `validate_model.py`
- Logging JSON lines (nie plain text)

### Phase 3 — /transcribe endpoint
**Dodane:**
- Walidacja `language` code (invalid ISO 639-1 → 400)
- Expanded docstring z **gotcha** o lazy segments
- Kod w pseudo-pythonie pokazuje jak materializować generator

**Dlaczego:** Brakowało `language` validation, gotcha było niedokumentowane

### Phase 4 — pytest tests
**Dodane:**
- `test_invalid_language_code_returns_400`
- `test_transcribe_timeout_returns_504` (long audio, 6+ min silence)
- `test_concurrent_requests_serialize` (threading test)
- `test_transcribe_case_insensitive` (use `.lower()` w asserts)

**Dlaczego:** Pokrycie edge case'ów, case sensitivity was undefined

### Phase 5 — Logging + polish
**Zmiana podejścia:**
- Modularization już **zrobiona w Phase 2** (nie Phase 5)
- Phase 5 teraz fokus na logging calls + docstrings
- Nie ma "refactoru" bo code już jest czysty

**Dlaczego:** Lepszy mental model — structure first, logging second

### Phase 6 — Dokumentacja
**Znacznie rozszerzone:**
- **Troubleshooting table** (8 common issues + solutions)
- **Performance expectations** (CUDA ms/min, CPU times)
- **Known limitations** (sequential, no cancellation, etc.)
- Detailed `CLAUDE.md` updates (operational rules, health check)
- Root `CLAUDE.md` gets whisper reference + link

**Dlaczego:** Nowa osoba czyta to i wie co robić (nie "czemu service nie działa?!")

---

## Statystyka zmian

| Plik | Przed | Po | Delta |
|---|---|---|---|
| decisions.md | 295 | 350 | +55 (D16, D17) |
| phases.md | 355 | 497 | +142 (details everywhere) |
| **Total PLAN/** | 720 | 875 | +155 |

---

## Co naprawiliśmy w oparciu o burze mózgów

| Punkt | Co było | Co jest teraz |
|---|---|---|
| **Lazy segments gotcha** | Niejasne | Dokumentowane w D17, pseudo-code w Phase 3 |
| **CUDA fallback transparency** | Brak info | Detailed w Phase 1 + troubleshooting table |
| **Model validation pre-start** | Brak | validate_model.py w Phase 1 + start.sh check |
| **Executor thread monitoring** | Brak | Accepted: nie rób (zbyt complex), dokumentuj limit |
| **Test edge cases** | Niekompletna | +4 new tests (504, concurrent, invalid lang, case) |
| **Code size risky** | Ryzyko >200 linii | Modularyzacja od razu (D16), all <60 linii |
| **ThreadPoolExecutor(1)** | Zaakceptowany | Zaakceptowany + dokumentacja limitations |
| **JSON logging library** | Undefined | D17: custom formatter, no external deps |

---

---

## Patche zaaplikowane post-brainstorm (2026-04-08)

### PATCH 1: api_spec.md — /ping endpoint + language="unknown"

**Zmiany:**
- Dodano `/ping` endpoint (lightweight, 200 OK, nie wymaga modelu)
- Language field może być `"unknown"` (silent audio case)
- Błąd 400 `invalid_language` dla kodów spoza ISO 639-1
- Dodano sekcję "Wspierane kody języków" (ISO 639-1 lista)

**Rationale:** `/health` niedostępna podczas warmup. `/ping` pozwala klientowi sprawdzić czy serwer żyje.

### PATCH 2: phases.md — Phase 2 /ping endpoint

**Zmiany:**
- Phase 2 teraz zawiera `/ping` route
- Acceptance test pokazuje `/ping` dostępne zaraz, `/health` po warmup

### PATCH 3: phases.md — Phase 3 validation order + language="unknown"

**Zmiany:**
- Explicit validation order (7 kroków) zamiast vague list
- **PRE-CHECK base64 size** przed decode (33% overhead check)
- Walidacja ISO 639-1 codes (reject "zh-CN", "yue", itd.)
- Silent audio handling: `language="unknown"`, `language_probability=null`
- Pseudo-code `_do_transcribe` pokazuje logic dla detect vs forced vs silent

**Rationale:** Wcześniej validation order było niejasne. Teraz fail-fast z czytelnym porządkiem.

### PATCH 4: phases.md — Phase 4 long_silence_audio fixture

**Zmiany:**
- Nowy fixture `long_silence_audio()` — 6 minut ciszy (do timeout testing)
- Test list zawiera `test_invalid_language_code_returns_400`
- Timeout test oznaczony `@pytest.mark.slow` (skip by default, ~300s runtime)

**Rationale:** Wcześniej nie było fixtury na long audio. Teraz można testować timeout.

### PATCH 5: phases.md — Phase 5 request_id logging detail

**Zmiany:**
- Konkretny pseudocode: request_id w route, log completion w executor
- Rationale: debugowanie sekwencji requestów w logach
- Acceptance test pokazuje format JSON logu z request_id

**Rationale:** Wcześniej request_id było _nice-to-have_. Teraz dokumentowanie clear.

### PATCH 6: phases.md — Phase 6 timeout + concurrent behavior

**Zmiany:**
- Dodano "Request timeout: 300 seconds" do Performance section
- Dodano "Concurrent requests: Sequential" do Known Limitations

**Rationale:** Users powinni wiedzieć że long audio timeout'uje, i że requesty się serializują.

---

## Ready to implement? ✅

Plan jest teraz:
- ✅ **Konkretny** — każdy plik ma line-count estimate (`server.py ~60`, itd.)
- ✅ **Testable** — każda faza ma acceptance criteria z komendami do uruchomienia
- ✅ **Debuggable** — troubleshooting table + performance expectations + logging design
- ✅ **Modularny** — struktura zdefinowana od start (nie refactor w Phase 5)
- ✅ **Dokumentowany** — README + CLAUDE.md + root CLAUDE.md updates

**Następny krok:** Implementacja Phase 1

---

## User decyzje (post-brainstorm)

| Pytanie | Wybór | Implementacja |
|---------|-------|----------------|
| Silent audio (language=?) | `language="unknown"` | ✅ Phase 3 pseudo-code |
| Language validation scope | ISO 639-1 only (~200 codes) | ✅ Phase 3 validation |
| TestClient fixture scope | `scope="session"` (szybko) | ✅ Phase 4 conftest.py |

---

## Znalezione issue'i (brainstorm team)

| Issue | Severity | Fix |
|-------|----------|-----|
| CUDA detection order (torch missing) | HIGH | ✅ Noted in Phase 1 |
| MAX_BYTES=25MB + timeout=300s asymmetry | HIGH | ✅ Phase 6 docs: timeout warning |
| Validation order niejasna | MEDIUM | ✅ PATCH 3: explicit 7-step order |
| State machine niejasna | MEDIUM | ✅ Phase 2 notes |
| Device context mismatch | MEDIUM | ✅ Phase 1 notes |
| Model loading race | MEDIUM | ✅ Phase 2: lifespan is sync |
| Real model tests = 8+ min | MEDIUM | ✅ PATCH 4: scope="session" |
| request_id single-thread | LOW | ✅ PATCH 5: documented |
| language_probability null | LOW | ✅ PATCH 3: documented |

---

## Pytania decyzyjne (pre-brainstorm, answered)

| Q | Rekomendacja | Status |
|---|---|---|
| Ad 1: Lazy segments materializacja | Trzymaj `list(segments)`. Add comment. | ✅ D17 |
| Ad 2: CUDA fallback signaling | Logs + Phase 1 check. No runtime fallback. | ✅ Phase 1, 6 |
| Ad 3: Model validation pre-start | `validate_model.py` + `start.sh` check | ✅ Phase 1, 2 |
| Ad 4: Executor monitoring | Skip fancy. Document limitations. | ✅ Phase 6 |
| Ad 5: Test edge cases | Add 504, concurrent, invalid lang, case-insensitive | ✅ Phase 4 |
| Ad 6: Code modularization | D16: 4 pliki, każdy <200 linii | ✅ Phase 2 |
| Ad 7: ThreadPoolExecutor(1) | Keep. Document sequential + no-cancel limits. | ✅ Phase 6 |
