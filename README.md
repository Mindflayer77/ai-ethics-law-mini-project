# Audyt licencji zależności oprogramowania AI

**Autor:** Mateusz Biedka, nr indeksu: 263527

**Temat:** 1 — Audyt licencji w repozytorium

**Kurs:** Aspekty prawne, społeczne i etyczne w AI, PWr 2025/2026

> Lista tematów: [Zasady zaliczenia — Menu mini-projektów](https://github.com/laugustyniak/ai-ethics-law-course/blob/main/Zasady%20zaliczenia.md#menu-mini-projekt%C3%B3w)

---

## Quick Start

```bash
uv sync                        # zainstaluj zależności
# Opcjonalnie — klucze API do modułu LLM doradcy:
cp .env.example .env           # uzupełnij OPENAI_API_KEY lub ANTHROPIC_API_KEY

# Skanowanie bieżącego projektu (raport tekstowy)
uv run src/main.py .

# Raport HTML (domyślnie wyniki/raport_licencji.html)
uv run src/main.py . --format html --output wyniki/raport_licencji.html

# Tryb CI — kod wyjścia 1 jeśli wykryto licencje silnego copyleft
uv run src/main.py . --check

# Sugestia licencji przez LLM (wymaga klucza API)
uv run src/main.py . --suggest-license
```

---

## Cel projektu

Narzędzie automatycznie skanuje zależności projektów Python/Node.js, pobiera informacje o ich licencjach z rejestrów PyPI i npm, klasyfikuje je pod względem ryzyka prawnego (permissive / słabe copyleft / silne copyleft / własnościowe) i generuje raport z rekomendacjami. Cel: pomoc deweloperom w identyfikacji potencjalnych konfliktów licencyjnych - szczególnie istotnych przy wyborze między projektem otwartym a komercyjnym.

Projekt odpowiada na pytanie: **czy mój projekt AI może zostać zamkniętoźródłowy lub komercyjny, biorąc pod uwagę licencje bibliotek, których używam?**

---

## Powiązanie z projektem grupowym

[Jak mini-projekt wiąże się z Waszym projektem naukowo-wdrożeniowym? Jeśli nie — napisz dlaczego wybrałeś ten temat.]

Projekt jest bezpośrednio związany z każdym projektem wykorzystujący język programowania python lub javascript / typescript. W naszym przypadku tworzymy kod projektu naukowo-wdrożeniowego w języku python. Utworzony tutaj projekt może być przydatny w przypadku gdy będziemy chcieli udostępnić nasze repozytorium publicznie lub wykorzystać rozwiązania do celów komerycjnych.

---

## Architektura systemu

```
src/
├── licencje.py      — baza 20+ licencji z klasyfikacją ryzyka i macierzą kompatybilności
├── skaner.py        — skaner plików manifestów (pyproject.toml, requirements.txt, package.json...)
├── pobieracz.py     — pobieranie metadanych z PyPI / npm API z cache 24h
├── analizator.py    — silnik analizy: klasyfikacja ryzyka, wykrywanie konfliktów
├── raport.py        — generator raportów HTML (SVG chart) / JSON / tekstowy
├── doradca_llm.py   — doradca LLM (OpenAI / Anthropic) sugerujący licencję dla projektu
└── main.py          — CLI (click): --check, --strict, --format, --suggest-license
.github/workflows/
└── license-audit.yml — CI/CD: blokada PR przy wykryciu wysokiego ryzyka
```

## Wymagania

Projekt korzysta z [uv](https://docs.astral.sh/uv/) — szybkiego menedżera pakietów Python.

```bash
# Instalacja uv (jeśli nie masz)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalacja zależności
uv sync
```

**Zmienne środowiskowe** (opcjonalne — tylko do modułu LLM doradcy):

```bash
cp .env.example .env
# Uzupełnij klucze w .env:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

## Uruchomienie

```bash
# Podstawowe skanowanie (raport tekstowy w konsoli)
uv run src/main.py .

# Pozwala na określenie głębokości skanowania ( przy 0 skanujemy tylko ROOT repozytorium) 
uv run src/main.py . --depth 0

# Raport HTML z wykresem SVG
uv run src/main.py . --format html --output wyniki/raport_licencji.html

# Raport JSON (maszynowo czytelny)
uv run src/main.py . --format json --output wyniki/raport_licencji.json

# Tryb CI — exit code 1 przy silnym copyleft lub licencjach własnościowych
uv run src/main.py . --check

# Tryb strict — dodatkowo blokuje słabe copyleft i nieznane
uv run src/main.py . --check --strict

# Sugestia licencji przez LLM
uv run src/main.py . --suggest-license --llm-provider openai

# Testy jednostkowe
uv run pytest tests/test_audyt_licencji.py -v
```

## Wyniki

### Bieżący projekt (`pyproject.toml`, 13 zależności bezpośrednich)

| Poziom ryzyka | Liczba | % | Przykłady |
|---|---|---|---|
| ✅ Bezpieczne (permissive) | 13 | 100% | MIT, Apache-2.0, BSD-3-Clause, PSF-2.0 |
| ⚠️ Słabe copyleft | 0 | 0% | — |
| 🔴 Silne copyleft | 0 | 0% | — |
| 🔒 Własnościowe | 0 | 0% | — |
| ❓ Nieznane | 0 | 0% | — |

Rozkład licencji w bieżącym projekcie:
- `openai`, `requests`, `packaging`, `google-genai` → Apache-2.0
- `anthropic`, `loguru` → MIT
- `python-dotenv`, `pandas`, `jinja2`, `jupyter`, `ipykernel`, `click` → BSD-3-Clause
- `matplotlib` → PSF-2.0

**Wniosek:** Projekt korzysta wyłącznie z licencji permissive — może być swobodnie komercjalizowany bez konieczności otwierania kodu źródłowego.

### Pełne skanowanie (cały workspace: projekt + `tmp/llama`, `tmp/nextjs`, `tmp/transformers`)

Skanowanie przeprowadzono na kilku repozytoriach open-source pobranych lokalnie w celu analizy porównawczej. Przeanalizowano **1 157 zależności** z ekosystemów PyPI i npm.

| Poziom ryzyka | Liczba | % | Kluczowe pakiety |
|---|---|---|---|
| ✅ Bezpieczne (permissive) | 1081 | 93,4% | MIT, Apache-2.0, BSD-3-Clause, ISC, CC0-1.0 |
| ⚠️ Słabe copyleft | 15 | 1,3% | `psycopg2` (LGPL-2.1), `fpdf` (LGPL), `py7zr` (LGPL), `tqdm` (MPL-2.0), `certifi` (MPL-2.0) |
| 🔴 Silne copyleft | 1 | 0,1% | `ffmpeg-static` (GPL-3.0) — plik testowy w turbopack Next.js |
| 🔒 Własnościowe | 1 | 0,1% | `pymupdf` — podwójna licencja AGPL-3.0 / komercyjna (Artifex) |
| ❓ Nieznane | 59 | 5,1% | `rouge`, `dotenv`, `@next/swc`, `react-builtin` i 55 innych (głównie npm) |

**Konflikty licencyjne:** 0 wykrytych.

**Szczegółowe raporty HTML:**
- [wyniki/raport_licencji.html](wyniki/raport_licencji.html) — skanowanie tego projektu
- [wyniki/raport_ai_research_assistant.html](wyniki/raport_ai_research_assistant.html) — projekt grupowy AI Research Assistant (13 dep.)
- [wyniki/raport_transformers.html](wyniki/raport_transformers.html) — Hugging Face Transformers (30 dep.)
- [wyniki/raport_llama.html](wyniki/raport_llama.html) — Llama Recipes (Meta, PyPI)
- [wyniki/raport_nextjs.html](wyniki/raport_nextjs.html) — Next.js (npm)

### Rekomendacje licencji wygenerowane przez LLM

Dla dwóch repozytoriów uruchomiono moduł doradcy LLM (OpenAI), który wygenerował rekomendacje na podstawie wykrytego profilu licencyjnego:

- [wyniki/rekomendacja_licencji_llm-transformers.md](wyniki/rekomendacja_licencji_llm-transformers.md) — LLM rekomenduje utrzymanie **Apache-2.0** (zgodność z zależnościami LGPL, ochrona patentowa).
- [wyniki/rekomendacja_licencji_llm-nextjs.md](wyniki/rekomendacja_licencji_llm-nextjs.md) — LLM rekomenduje **MIT**, ostrzega przed `ffmpeg-static` (GPL-3.0) jako zagrożeniem dla dystrybucji zamkniętego kodu.
- [wyniki/rekomendacja_licencji_llm-llama.md](wyniki/rekomendacja_licencji_llm-llama.md) — LLM rekomenduje **Apache-2.0** dla Llama Cookbook (Meta): kompatybilność z LGPL/MPL, ochrona patentowa, wsparcie wymogów AI Act dot. przejrzystości; wskazuje `pymupdf` jako jedyną własnościową zależność do przeglądu.

### Projekt grupowy: AI Research Assistant
Przeanalizowano `pyproject.toml` repozytorium AI Research Assistant - nasz projekt grupowy.

| Poziom ryzyka | Liczba | % | Pakiety |
|---|---|---|---|
| ✅ Bezpieczne (permissive) | 12 | 92,3% | MIT, Apache-2.0, BSD-3-Clause i inne |
| ⚠️ Słabe copyleft | 1 | 7,7% | `tqdm` (MPL-2.0) |
| 🔴 Silne copyleft | 0 | 0% | — |
| 🔒 Własnościowe | 0 | 0% | — |
| ❓ Nieznane | 0 | 0% | — |

Kluczowe obserwacje:
- Profil licencyjny jest bezpieczny - projekt może być komercjalizowany lub udostępniony publicznie bez ryzyka copyleft.
- `tqdm` (MPL-2.0) to jedyna zależność wymagająca uwagi: copyleft na poziomie pliku - modyfikacje samego `tqdm` trzeba by udostępnić, ale własny kod projektu pozostaje prywatny.

**Raport HTML:** [wyniki/raport_ai_research_assistant.html](wyniki/raport_ai_research_assistant.html)

## Wnioski merytoryczne

### 1. Ryzyko prawne licencji copyleft w projektach AI

Licencje **GPL-3.0** i **AGPL-3.0** tworzą tzw. „efekt copyleft" — każdy projekt korzystający z biblioteki GPL musi sam zostać opublikowany pod GPL. W kontekście AI jest to szczególnie problematyczne:

- Wiele bibliotek ML/AI (PyTorch, TensorFlow) używa Apache-2.0 lub BSD, ale część narzędzi (np. niektóre modele finetuned) może być objęta GPL lub AGPL.
- **AGPL-3.0** jest wyjątkowo rygorystyczne: wymaga udostępnienia kodu nawet przy dostępie przez sieć (SaaS) - co dotyczy praktycznie każdego API opartego na modelu AI.
- Naruszenie licencji GPL może skutkować **cofnięciem prawa do korzystania** i roszczeniami odszkodowawczymi.

### 2. Luki w regulacjach: AI Act a licencje

Rozporządzenie **EU AI Act** (2024/1689) wprowadza obowiązki przejrzystości, ale **nie reguluje bezpośrednio kwestii licencji** użytych bibliotek. Jednak:
- Art. 11 (dokumentacja techniczna) oraz Art. 53 (GPAI) wymagają dokumentowania komponentów systemu — co obejmuje biblioteki open-source.
- Brak audytu licencji może być traktowany jako brak należytej staranności (due diligence).
- **Rekomendacja:** Automatyczny audyt licencji powinien być częścią procesu CI/CD każdego systemu AI.

### 3. Problem nieznanych licencji

Pakiety bez zadeklarowanej licencji są z prawnego punktu widzenia **domyślnie zastrzeżone** (All Rights Reserved). Używanie ich w projekcie komercyjnym bez uzyskania wyraźnej zgody autora jest naruszeniem prawa autorskiego. Dlatego jeśli któraś licencja jest nieznana skaner identyfikuje te przypadki i alarmuje.

### 4. Problem nieznanych licencji w ekosystemie npm

5% zależności (59 pakietów) w pełnym skanie nie miało rozpoznanej licencji — niemal wyłącznie z ekosystemu npm. Wśród nich: wewnętrzne pakiety Next.js (`@next/swc`, `react-builtin`, `react-dom-builtin`) oraz pakiety testowe. Prawnie, brak deklaracji licencji oznacza **domyślne zastrzeżenie wszelkich praw** (All Rights Reserved) — nawet jeśli kod jest publicznie dostępny. Używanie takich pakietów w projekcie komercyjnym bez zgody autora może stanowić naruszenie praw autorskich.

Biblioteki AI przetwarzające dane osobowe (np. SDK do modeli językowych) mogą nakładać dodatkowe warunki przetwarzania danych. Analiza licencji powinna być uzupełniona o analizę warunków usługi i DPA (Data Processing Agreement).

## Ograniczenia

- Skaner analizuje bezpośrednie zależności (top-level) - nie sprawdza zależności pośrednich (transitive). Pełny audyt wymagałby rozwiązania drzewa zależności.
- Klasyfikacja ryzyka jest uproszczona - rzeczywista analiza prawna wymaga konsultacji z prawnikiem.
- Moduł LLM doradcy generuje jedynie sugestie które nie powinny być traktowane jak porada prawna.
- Brak wsparcia dla plików Cargo.toml (Rust), go.mod (Go), pom.xml (Java/Maven).
- Kompatybilność licencji zależy od konkretnego sposobu użycia (linkowanie statyczne vs dynamiczne, modyfikacja vs użycie) - skaner stosuje uproszczenia.
- Zależności z plików testowych (np. `ffmpeg-static` w fixture testowym turbopack) są traktowane tak samo jak zależności produkcyjne - co może zawyżać ocenę ryzyka dla kodu core projektu.

## Źródła

- [SPDX License List](https://spdx.org/licenses/) — oficjalny spis identyfikatorów licencji SPDX
- [Choose a License](https://choosealicense.com/appendix/) — porównanie licencji open-source
- [tldrlegal.com](https://tldrlegal.com/) — opisy licencji w przystępnym języku
- [FSF License Compatibility](https://www.gnu.org/licenses/license-compatibility.html) — macierz kompatybilności GNU
- [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) — Rozporządzenie PE i Rady (UE) 2024/1689
- [PyPI JSON API](https://docs.pypi.org/api/json/) — dokumentacja API PyPI
- [npm Registry API](https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md) — dokumentacja npm Registry
- [Open Source Initiative — Licenses](https://opensource.org/licenses) — zatwierdzone licencje OSI
- [EUPL Compatibility](https://joinup.ec.europa.eu/collection/eupl/eupl-compatibility-explainer) — kompatybilność licencji EUPL

