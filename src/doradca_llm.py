"""
Moduł doradcy licencji oparty na LLM.

Na podstawie:
1. Opisu projektu (README.md lub podanego przez użytkownika)
2. Listy zależności z ich licencjami

LLM sugeruje optymalną licencję dla projektu, uzasadniając wybór
w kontekście prawnym i biznesowym.

Obsługuje: OpenAI (domyślnie), Anthropic (fallback).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from analizator import WynikAnalizy
from licencje import PoziomRyzyka


# ---------------------------------------------------------------------------
# Stałe
# ---------------------------------------------------------------------------

_PROMPT_SYSTEMOWY = """Jesteś ekspertem od prawa własności intelektualnej, licencji open-source
i zgodności prawnej oprogramowania. Specjalizujesz się w prawie EU, w tym AI Act (Rozporządzenie (UE) 2024/1689)
i regulacjach dotyczących IP.

Odpowiadasz po polsku, merytorycznie i konkretnie.
Twoje rekomendacje są praktyczne i uwzględniają zarówno aspekty prawne, jak i biznesowe.
Odwołujesz się do konkretnych artykułów ustaw i regulacji gdy to możliwe."""

_PROMPT_SZABLONU = """Przeprowadź analizę licencyjną projektu i zasugeruj odpowiednią licencję.

## Informacje o projekcie

{opis_projektu}

## Wyniki skanowania zależności

Znaleziono {liczba_zaleznie} zależności:
- Bezpieczne (permissive): {bezpieczne}
- Słabe copyleft (LGPL/MPL): {slabe_copyleft}
- Silne copyleft (GPL/AGPL): {silne_copyleft}
- Własnościowe: {wlasnosci}
- Nieznane: {nieznane}

### Szczegóły zależności z silnym copyleft:
{lista_silne_copyleft}

### Szczegóły zależności ze słabym copyleft:
{lista_slabe_copyleft}

### Konflikty kompatybilności:
{konflikty}

## Pytania do analizy

1. Jaką licencję rekomendowałbyś dla tego projektu i dlaczego?
   Uwzględnij: (a) wymogi wynikające z użytych zależności, 
   (b) intencję twórcy (open-source vs komercyjne), 
   (c) AI Act i kwestię przejrzystości systemów AI.

2. Czy istnieją problemy prawne wynikające z obecnego zestawu licencji?
   Jeśli tak — co należy zrobić?

3. Czy z perspektywy AI Act (Rozporządzenie (UE) 2024/1689) wybór licencji 
   ma znaczenie dla wymogów przejrzystości i odpowiedzialności?

Odpowiedz strukturyzowanym raportem z sekcjami:
- Rekomendowana licencja + uzasadnienie prawne
- Zidentyfikowane ryzyka
- Zgodność z AI Act
- Konkretne kroki do podjęcia"""


def _buduj_prompt_uzytkownika(
    opis_projektu: str,
    wynik: WynikAnalizy,
) -> str:
    """Buduje prompt dla LLM na podstawie opisu projektu i wyników analizy."""
    stats = wynik.statystyki_ryzyka

    # Listy zależności problematycznych
    silne_copyleft_deps = wynik.filtruj_po_ryzyku(PoziomRyzyka.SILNE_COPYLEFT)
    slabe_copyleft_deps = wynik.filtruj_po_ryzyku(PoziomRyzyka.SLABE_COPYLEFT)

    lista_silne = "\n".join(
        f"  - {a.zaleznosc.nazwa} ({a.licencja_spdx or a.wynik_pobierania.licencja_surowa})"
        for a in silne_copyleft_deps
    ) or "  Brak"

    lista_slabe = "\n".join(
        f"  - {a.zaleznosc.nazwa} ({a.licencja_spdx or a.wynik_pobierania.licencja_surowa})"
        for a in slabe_copyleft_deps
    ) or "  Brak"

    konflikty_str = "\n".join(
        f"  - {k.pakiet_a} ({k.licencja_a}) ↔ {k.pakiet_b} ({k.licencja_b}): {k.opis[:100]}"
        for k in wynik.konflikty
    ) or "  Brak wykrytych konfliktów"

    return _PROMPT_SZABLONU.format(
        opis_projektu=opis_projektu,
        liczba_zaleznie=wynik.liczba_zaleznie,
        bezpieczne=stats[PoziomRyzyka.BEZPIECZNA],
        slabe_copyleft=stats[PoziomRyzyka.SLABE_COPYLEFT],
        silne_copyleft=stats[PoziomRyzyka.SILNE_COPYLEFT],
        wlasnosci=stats[PoziomRyzyka.WLASNOSCI],
        nieznane=stats[PoziomRyzyka.NIEZNANA],
        lista_silne_copyleft=lista_silne,
        lista_slabe_copyleft=lista_slabe,
        konflikty=konflikty_str,
    )


def _pobierz_opis_projektu(katalog: Path) -> str:
    """
    Próbuje wczytać opis projektu z README.md.
    Jeśli nie istnieje, zwraca ogólny opis.
    """
    for nazwa_pliku in ("README.md", "readme.md", "README.rst", "README.txt"):
        readme = katalog / nazwa_pliku
        if readme.exists():
            tekst = readme.read_text(encoding="utf-8", errors="replace")
            # Wyciągnij pierwsze 2000 znaków (cel projektu, opis)
            return tekst[:2000]
    return "Projekt Python — brak pliku README.md."


def sugeruj_licencje_openai(
    opis_projektu: str,
    wynik: WynikAnalizy,
    model: str = "gpt-4.1-nano",
) -> str:
    """
    Używa OpenAI do sugestii licencji dla projektu.

    Args:
        opis_projektu: Opis projektu (np. z README.md).
        wynik: Wynik analizy zależności.
        model: Nazwa modelu OpenAI.

    Returns:
        Odpowiedź LLM z rekomendacją licencji.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return "Błąd: Biblioteka openai nie jest zainstalowana. Uruchom: uv add openai"

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-..."):
        return "Błąd: Brak klucza OPENAI_API_KEY w zmiennych środowiskowych."

    klient = OpenAI()
    prompt = _buduj_prompt_uzytkownika(opis_projektu, wynik)

    logger.info("Wysyłanie zapytania do OpenAI ({})...", model)
    try:
        odpowiedz = klient.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _PROMPT_SYSTEMOWY},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2500,
            temperature=0.3,
        )
        return odpowiedz.choices[0].message.content or "Brak odpowiedzi."
    except Exception as blad:
        logger.error("Błąd OpenAI: {}", blad)
        return f"Błąd podczas komunikacji z OpenAI: {blad}"


def sugeruj_licencje_anthropic(
    opis_projektu: str,
    wynik: WynikAnalizy,
    model: str = "claude-3-5-haiku-20241022",
) -> str:
    """
    Używa Anthropic Claude do sugestii licencji dla projektu.

    Args:
        opis_projektu: Opis projektu (np. z README.md).
        wynik: Wynik analizy zależności.
        model: Nazwa modelu Anthropic.

    Returns:
        Odpowiedź LLM z rekomendacją licencji.
    """
    try:
        import anthropic
    except ImportError:
        return "Błąd: Biblioteka anthropic nie jest zainstalowana. Uruchom: uv add anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or "test" in api_key.lower():
        return "Błąd: Brak klucza ANTHROPIC_API_KEY w zmiennych środowiskowych."

    klient = anthropic.Anthropic()
    prompt = _buduj_prompt_uzytkownika(opis_projektu, wynik)

    logger.info("Wysyłanie zapytania do Anthropic ({})...", model)
    try:
        wiadomosc = klient.messages.create(
            model=model,
            max_tokens=2500,
            system=_PROMPT_SYSTEMOWY,
            messages=[{"role": "user", "content": prompt}],
        )
        return wiadomosc.content[0].text
    except Exception as blad:
        logger.error("Błąd Anthropic: {}", blad)
        return f"Błąd podczas komunikacji z Anthropic: {blad}"


def sugeruj_licencje(
    wynik: WynikAnalizy,
    katalog_projektu: Path,
    opis_niestandardowy: str | None = None,
    dostawca: str = "openai",
) -> str:
    """
    Główna funkcja doradcy licencji — próbuje użyć wybranego LLM.

    Args:
        wynik: Wynik analizy zależności.
        katalog_projektu: Katalog projektu (do wczytania README).
        opis_niestandardowy: Opcjonalny własny opis projektu.
        dostawca: "openai" lub "anthropic".

    Returns:
        Rekomendacja licencji jako tekst.
    """
    load_dotenv()

    opis = opis_niestandardowy or _pobierz_opis_projektu(katalog_projektu)

    if dostawca == "anthropic":
        return sugeruj_licencje_anthropic(opis, wynik)
    else:
        wynik_openai = sugeruj_licencje_openai(opis, wynik)
        # Fallback na Anthropic jeśli OpenAI nie ma klucza
        if "Błąd: Brak klucza" in wynik_openai:
            logger.info("OpenAI niedostępny — próbuję Anthropic...")
            return sugeruj_licencje_anthropic(opis, wynik)
        return wynik_openai
