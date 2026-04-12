# Test fixtures — audio samples

All samples sourced from [Wikimedia Commons](https://commons.wikimedia.org)
and used **unmodified** under their respective licenses (Public Domain,
CC BY, CC BY-SA). Files are Ogg Vorbis — `faster-whisper` decodes them
natively via the bundled PyAV/ffmpeg libraries, no extra codec install
needed.

## Coverage matrix

```
                         long  female  UK    PL-diacritics  proper
                         form  voice   acc.  stress-test    nouns
────────────────────────────────────────────────────────────────────
pl_chrzaszcz.ogg          -      -      -        ✓             -
pl_alphabet.ogg           ~      -      -        ✓✓            -
pl_smartfon.ogg           ✓      -      -        ~             -
en_fox.ogg                -      -      -        -             -
en_rolling_stone.ogg      -      -      -        -             -
en_uk_north_wind.ogg      ✓      ?      ✓        -             -
en_us_election.ogg        -      ?      -        -             ✓
```

Gaps: verified female voice for either language (current inferences
are from Wikimedia categories, not file metadata), dedicated numbers/
dates sample.

---

## Polish fixtures

### pl_chrzaszcz.ogg — 9.21 s, 86 KB

- **Title:** Polish Tongue twister - Chrząszcz
- **Author:** Adam78 (Wikimedia Commons contributor)
- **License:** [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)
- **Source:** <https://commons.wikimedia.org/wiki/File:Polish_Tongue_twister_-_Chrz%C4%85szcz.ogg>
- **Content (exact):** "W Szczebrzeszynie chrząszcz brzmi w trzcinie
  i Szczebrzeszyn z tego słynie, wół go pyta — panie chrząszczu,
  po cóż pan tak brzęczy w gąszczu?"
- **Test purpose:** classic tongue twister — aggressive probe for
  Polish diacritics (`ą ę ó`) and sibilant clusters (`szcz`).

### pl_alphabet.ogg — 29.22 s, 316 KB

- **Title:** Polish Alphabet
- **Author:** Wyksztalcioch (Wikimedia Commons contributor)
- **License:** Public Domain (released by copyright holder)
- **Source:** <https://commons.wikimedia.org/wiki/File:Pl-Polish_Alphabet.ogg>
- **Content (exact):** "a ą b c ć d e ę f g h i j k l ł m n ń o ó p r
  s ś t u w y z ź ż" (each letter spoken individually)
- **Test purpose:** **diacritics stress test** — every Polish special
  letter explicitly named. If quantization degrades, this is where it
  shows first. Upstream file uses `.oga` extension; renamed to `.ogg`
  here (same Vorbis codec) for directory consistency.

### pl_smartfon.ogg — 39.45 s, 489 KB

- **Title:** Pl-Smartfon (Wikipedia article fragment read aloud)
- **Author/Speaker:** Borys Kozielski (male voice)
- **License:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Source:** <https://commons.wikimedia.org/wiki/File:Pl-Smartfon.ogg>
- **Content (opening, verifiable against [pl.wikipedia.org/wiki/Smartfon](https://pl.wikipedia.org/wiki/Smartfon)):**
  "Smartfon (ang. smartphone) – przenośne, multimedialne urządzenie,
  łączące w sobie funkcje telefonu komórkowego i komputera przenośnego..."
  The full 39 s clip reads further into the article body — Wikimedia
  does not document exactly where the reading stops.
- **Test purpose:** **long-form natural reading voice** — tests segment
  merging and `duration_s` reporting. Assertion strategy: `startswith("Smartfon")`
  and `"telefonu komórkowego" in text` — do NOT write exact-match
  assertion across the whole clip.

---

## English fixtures

### en_fox.ogg — 3.81 s, 64 KB

- **Title:** Audio Sample - The Quick Brown Fox Jumps Over The Lazy Dog
- **Author:** RussmanJr (Wikimedia Commons contributor)
- **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Source:** <https://commons.wikimedia.org/wiki/File:Audio_Sample_-_The_Quick_Brown_Fox_Jumps_Over_The_Lazy_Dog.ogg>
- **Content (exact):** "The quick brown fox jumps over the lazy dog."
- **Test purpose:** English pangram — short smoke test covering all
  ASCII letters.

### en_rolling_stone.ogg — 2.66 s, 61 KB

- **Title:** En-us-a rolling stone gathers no moss
- **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Source:** <https://commons.wikimedia.org/wiki/File:En-us-a_rolling_stone_gathers_no_moss.ogg>
- **Content (exact):** "A rolling stone gathers no moss."
- **Test purpose:** second short English sample, useful for parallel/
  batch tests without reusing the pangram.

### en_uk_north_wind.ogg — 36.43 s, 853 KB

- **Title:** Recording of speaker of British English (Received Pronunciation)
- **Author:** P. Roach (from the 2004 International Phonetic Association Handbook)
- **License:** [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)
  (also GFDL 1.2+)
- **Source:** <https://commons.wikimedia.org/wiki/File:Recording_of_speaker_of_British_English_(Received_Pronunciation).ogg>
- **Content (exact, verified via Wikimedia TimedText subtitles):**
  "The North Wind and the Sun were disputing which was the stronger,
  when a traveller came along wrapped in a warm cloak. They agreed
  that the one who first succeeded in making the traveller take his
  cloak off should be considered stronger than the other. Then the
  North Wind blew as hard as he could, but the more he blew the more
  closely did the traveller fold his cloak around him; and at last
  the North Wind gave up the attempt. Then the Sun shone out warmly,
  and immediately the traveller took off his cloak. And so the North
  Wind was obliged to confess that the Sun was the stronger of the two."
- **Test purpose:** **long-form English + UK Received Pronunciation** —
  fills two gaps in coverage. The IPA Handbook uses a canonical reading
  text so exact-match assertion is possible. Speaker gender not
  documented on Wikimedia.
- **Size note:** 853 KB — slightly over our 800 KB soft budget for
  fixtures, kept as-is because the Wikimedia MP3 transcode would
  introduce lossy double-compression that would muddy STT quality tests.

### en_us_election.ogg — 8.00 s, 83 KB

- **Title:** The Article establishes the manner of election
- **Author:** "Persian Poet Gal" (Wikimedia Commons contributor)
- **License:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Source:** <https://commons.wikimedia.org/wiki/File:The_Article_establishes_the_manner_of_election.ogg>
- **Content (exact):** "The Article establishes the manner of election
  and qualifications of members of each House."
- **Test purpose:** US English with **legal/government vocabulary**
  (proper nouns and capitalized institutional terms — a common STT
  failure mode). Listed as female-voice in Wikimedia category
  "Audio files of females speaking English" but the file page itself
  does not state speaker gender — treat the female tag as inferential,
  not authoritative.

---

## License compliance note

All files are **unmodified** — ShareAlike provisions do not propagate
to the rest of the repository. Three license families are present:

| License | Files | Attribution required | ShareAlike |
|---|---|---|---|
| Public Domain | `pl_alphabet.ogg` | courtesy only | no |
| CC BY 4.0 | `pl_smartfon.ogg` | yes | no |
| CC BY-SA 3.0 | `pl_chrzaszcz.ogg`, `en_uk_north_wind.ogg` | yes | if modified |
| CC BY-SA 4.0 | `en_fox.ogg`, `en_rolling_stone.ogg`, `en_us_election.ogg` | yes | if modified |

This file provides the required attribution and license notices for all
Wikimedia Commons samples. If you modify any audio file, document the
change in this README and license the derivative under the same CC BY-SA
version as the source (where applicable).
