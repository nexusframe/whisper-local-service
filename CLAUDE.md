# services/whisper — CLAUDE.md

**STATUS: ZBUDOWANY, DZIAŁAJĄCY.** Local STT microservice na `127.0.0.1:8765`.
Implementacja w pełni zakończona (5 faz). Produkcyjnie gotowy.

## Co to jest

Lokalny HTTP microservice do transkrypcji audio oparty o `faster-whisper`
(CTranslate2). Przyjmuje audio (base64 w JSON POST) na `127.0.0.1:8765`,
zwraca tekst. Model `large-v3` int8, ~3 GB VRAM, localhost only.

## Jeśli masz ten service zbudować

1. Przeczytaj `PLAN/README.md` → `PLAN/decisions.md` → `PLAN/api_spec.md`
   → `PLAN/phases.md` **w tej kolejności**
2. Wykonuj fazami z `PLAN/phases.md` (6 faz), każda ma kryterium akceptacji
3. Decyzje są już podjęte — nie spieraj się z planem. Jeśli coś jest
   fundamentalnie złe, zaproponuj zmianę w rozmowie z użytkownikiem,
   nie w kodzie
4. Zachowaj zakres — anti-cele w `PLAN/phases.md` (ostatnia sekcja) są celowe

## Jeśli chcesz użyć tego service z innego projektu

Sprawdź czy service jest uruchomiony:
```bash
curl -s http://127.0.0.1:8765/health | jq
```

Jeśli nie odpowiada → service nie został jeszcze zbudowany (patrz wyżej)
lub nie został uruchomiony. Żeby uruchomić (po zbudowaniu):
```bash
cd services/whisper && ./start.sh
```

API kontrakt → `PLAN/api_spec.md`. Po zbudowaniu kluczowe informacje
trafią do `README.md` tego katalogu.

Przykład użycia w Node.js:
```js
const res = await fetch('http://127.0.0.1:8765/transcribe', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    audio_base64: buffer.toString('base64'),
    language: 'pl',
  }),
});
const { text } = await res.json();
```

Przykład użycia w Python:
```python
import base64, requests
res = requests.post(
    "http://127.0.0.1:8765/transcribe",
    json={"audio_base64": base64.b64encode(audio_bytes).decode(), "language": "pl"},
    timeout=600,
)
text = res.json()["text"]
```

## Rzeczy o których Claude musi pamiętać

- **Nigdy** nie odpalaj `start.sh` w tle bez wyraźnej zgody użytkownika —
  to jest persistent service zajmujący VRAM
- **Nigdy** nie bindiuj na `0.0.0.0` — localhost only, trust boundary to OS
- **Nigdy** nie commituj `.env` ani `.venv/`
- **Nigdy** nie modyfikuj plików w `fixtures/` — są committed z Wikimedia
  Commons pod CC BY-SA, modyfikacja łamie attribution
- Jeśli VRAM issues — **najpierw** sprawdź czy inny proces nie zajmuje
  GPU (`nvidia-smi`). Jeśli GPU faktycznie wolny ale model nie wchodzi,
  fallback: zmień `WHISPER_MODEL=large-v3-turbo` w `.env` i restart
  (strata ~3-5% jakości za zysk ~1 GB VRAM)
- Python subprocess jest OK do debugowania, ale service docelowo jest
  HTTP — nie rób hybrydy
- Logi idą na `stdout` w formacie JSON lines — jeśli chcesz plik,
  redirectuj: `./start.sh 2>&1 | tee whisper.log`
- **Don't flatter**, be critical
