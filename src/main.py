"""
Narzędzie CLI do audytu licencji zależności projektu.

Użycie:
    uv run src/main.py [OPCJE] [KATALOG_PROJEKTU]

Przykłady:
    # Skanuj bieżący projekt, generuj raport HTML
    uv run src/main.py

    # Skanuj konkretny katalog
    uv run src/main.py /ścieżka/do/projektu

    # Tryb CI — wyjście z kodem 1 jeśli wykryto licencje wysokiego ryzyka
    uv run src/main.py --check

    # Tryb CI ścisły — błąd również dla słabego copyleft i nieznanych
    uv run src/main.py --check --strict

    # Generuj raport JSON (dla dalszego przetwarzania)
    uv run src/main.py --format json --output wyniki/licencje.json

    # Zapytaj LLM o rekomendację licencji
    uv run src/main.py --suggest-license

    # Tryb cichy — tylko raport tekstowy, bez pasków postępu
    uv run src/main.py --quiet

Kody wyjścia (dla CI/CD):
    0 — brak problemów (lub --check pominięty)
    1 — wykryto licencje wysokiego ryzyka (z --check)
    2 — błąd wykonania (np. brak pliku manifestu)
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from loguru import logger

# Dodaj katalog src do ścieżki Pythona (dla importów modułów)
_SRC_DIR = Path(__file__).parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from analizator import analizuj_zaleznie
from doradca_llm import sugeruj_licencje
from licencje import PoziomRyzyka
from pobieracz import pobierz_licencje_batch
from raport import (
    drukuj_raport_tekstowy,
    generuj_raport_html,
    generuj_raport_json,
)
from skaner import skanuj_projekt


# ---------------------------------------------------------------------------
# Konfiguracja loguru
# ---------------------------------------------------------------------------


def _konfiguruj_logowanie(cichy: bool) -> None:
    """Konfiguruje logowanie: cichy tryb wyłącza INFO, zachowuje WARNING+."""
    logger.remove()
    if cichy:
        logger.add(sys.stderr, level="WARNING", colorize=True)
    else:
        logger.add(sys.stderr, level="INFO", colorize=True, format="<dim>{time:HH:mm:ss}</dim> | {level} | {message}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command()
@click.argument(
    "katalog_projektu",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output", "-o",
    default=None,
    help="Ścieżka pliku wyjściowego (domyślnie: wyniki/raport_licencji.html lub .json).",
    type=click.Path(path_type=Path),
)
@click.option(
    "--format", "-f", "format_wyjscia",
    default="html",
    type=click.Choice(["html", "json", "text"], case_sensitive=False),
    help="Format wyjściowy raportu (domyślnie: html).",
    show_default=True,
)
@click.option(
    "--check", "-c",
    is_flag=True,
    default=False,
    help="Tryb CI: zakończ z kodem 1 jeśli wykryto licencje silnego copyleft/własnościowe.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Tryb ścisły CI: błąd również dla słabego copyleft i nieznanych licencji.",
)
@click.option(
    "--suggest-license",
    is_flag=True,
    default=False,
    help="Użyj LLM do rekomendacji licencji projektu (wymaga klucza API).",
)
@click.option(
    "--llm-provider",
    default="openai",
    type=click.Choice(["openai", "anthropic"], case_sensitive=False),
    help="Dostawca LLM dla rekomendacji licencji.",
    show_default=True,
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    default=False,
    help="Tryb cichy: wyświetlaj tylko ostrzeżenia i błędy.",
)
@click.option(
    "--project-name",
    default=None,
    help="Nazwa projektu w raporcie (domyślnie: nazwa katalogu).",
)
@click.option(
    "--depth", "-d",
    default=None,
    type=click.IntRange(min=0),
    help="Maksymalna głębokość skanowania podkatalogów (0 = tylko katalog główny, domyślnie: bez limitu).",
    metavar="POZIOM",
)
def cli(
    katalog_projektu: Path,
    output: Path | None,
    format_wyjscia: str,
    check: bool,
    strict: bool,
    suggest_license: bool,
    llm_provider: str,
    quiet: bool,
    project_name: str | None,
    depth: int | None,
) -> None:
    """
    🔍 Audyt licencji zależności projektu.

    Skanuje pliki manifestowe (requirements.txt, pyproject.toml, package.json)
    i sprawdza licencje pakietów z rejestrów PyPI i npm.

    KATALOG_PROJEKTU — katalog do skanowania (domyślnie: bieżący katalog).
    """
    load_dotenv()
    _konfiguruj_logowanie(quiet)

    katalog = katalog_projektu.resolve()
    nazwa_projektu = project_name or katalog.name

    # -----------------------------------------------------------------------
    # 1. Skanowanie zależności
    # -----------------------------------------------------------------------
    if not quiet:
        click.echo(f"\n🔍 Skanowanie katalogu: {katalog}")
        if depth is not None:
            click.echo(f"🔎 Głębokość skanowania: {depth} {'(tylko katalog główny)' if depth == 0 else f'poziom(y) podkatalogów'}")

    try:
        zaleznie = skanuj_projekt(katalog, maks_glebokosc=depth)
    except ValueError as blad:
        click.echo(f"❌ Błąd: {blad}", err=True)
        sys.exit(2)

    if not zaleznie:
        click.echo("⚠️  Nie znaleziono żadnych zależności. Sprawdź czy katalog zawiera pliki manifestowe.", err=True)
        sys.exit(2)

    if not quiet:
        click.echo(f"📦 Znaleziono {len(zaleznie)} zależności.")

    # -----------------------------------------------------------------------
    # 2. Pobieranie licencji z PyPI/npm
    # -----------------------------------------------------------------------
    if not quiet:
        click.echo("🌐 Pobieranie informacji o licencjach...")

    wyniki_pobierania = pobierz_licencje_batch(zaleznie, opoznienie=0.08)

    # -----------------------------------------------------------------------
    # 3. Analiza
    # -----------------------------------------------------------------------
    wynik = analizuj_zaleznie(zaleznie, wyniki_pobierania)

    # -----------------------------------------------------------------------
    # 4. Generowanie raportu
    # -----------------------------------------------------------------------
    if output is None:
        rozszerzenia = {"html": "html", "json": "json", "text": "txt"}
        output = katalog / "wyniki" / f"raport_licencji.{rozszerzenia[format_wyjscia]}"

    if format_wyjscia == "html":
        generuj_raport_html(wynik, output, nazwa_projektu)
        if not quiet:
            click.echo(f"📄 Raport HTML zapisany: {output}")
    elif format_wyjscia == "json":
        generuj_raport_json(wynik, output, nazwa_projektu)
        if not quiet:
            click.echo(f"📄 Raport JSON zapisany: {output}")
    elif format_wyjscia == "text":
        tekst = drukuj_raport_tekstowy(wynik, nazwa_projektu)
        if output and str(output) != "-":
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(tekst, encoding="utf-8")
            if not quiet:
                click.echo(f"📄 Raport TXT zapisany: {output}")
        else:
            click.echo(tekst)

    # -----------------------------------------------------------------------
    # 5. Podsumowanie w terminalu
    # -----------------------------------------------------------------------
    if not quiet:
        stats = wynik.statystyki_ryzyka
        click.echo("\n📊 Podsumowanie:")
        click.echo(f"   ✅ Bezpieczne:         {stats[PoziomRyzyka.BEZPIECZNA]}")
        click.echo(f"   ⚠️  Słabe copyleft:     {stats[PoziomRyzyka.SLABE_COPYLEFT]}")
        click.echo(f"   🔴 Silne copyleft:      {stats[PoziomRyzyka.SILNE_COPYLEFT]}")
        click.echo(f"   🔒 Własnościowe:        {stats[PoziomRyzyka.WLASNOSCI]}")
        click.echo(f"   ❓ Nieznane:            {stats[PoziomRyzyka.NIEZNANA]}")
        if wynik.konflikty:
            click.echo(f"   ⚡ Konflikty:          {len(wynik.konflikty)}")

    # -----------------------------------------------------------------------
    # 6. Rekomendacja LLM (opcjonalna)
    # -----------------------------------------------------------------------
    if suggest_license:
        if not quiet:
            click.echo(f"\n🤖 Zapytywanie {llm_provider.upper()} o rekomendację licencji...")
        rekomendacja = sugeruj_licencje(wynik, katalog, dostawca=llm_provider)
        click.echo("\n" + "─" * 60)
        click.echo("🤖 REKOMENDACJA LICENCJI (LLM):")
        click.echo("─" * 60)
        click.echo(rekomendacja)
        click.echo("─" * 60 + "\n")

        # Zapisz rekomendację LLM do pliku
        sciezka_rek = katalog / "wyniki" / "rekomendacja_licencji_llm.md"
        sciezka_rek.parent.mkdir(parents=True, exist_ok=True)
        sciezka_rek.write_text(
            f"# Rekomendacja licencji dla projektu {nazwa_projektu}\n\n"
            f"*Wygenerowano przez {llm_provider.upper()}*\n\n"
            f"{rekomendacja}\n",
            encoding="utf-8",
        )
        if not quiet:
            click.echo(f"💾 Rekomendacja zapisana: {sciezka_rek}")

    # -----------------------------------------------------------------------
    # 7. Tryb CI — kod wyjścia
    # -----------------------------------------------------------------------
    if check:
        problemy: list[str] = []

        silne = wynik.filtruj_po_ryzyku(PoziomRyzyka.SILNE_COPYLEFT)
        wlasnosci = wynik.filtruj_po_ryzyku(PoziomRyzyka.WLASNOSCI)
        konflikty = wynik.konflikty

        if silne:
            nazwy = ", ".join(a.zaleznosc.nazwa for a in silne)
            problemy.append(f"Licencje silnego copyleft: {nazwy}")
        if wlasnosci:
            nazwy = ", ".join(a.zaleznosc.nazwa for a in wlasnosci)
            problemy.append(f"Licencje własnościowe: {nazwy}")
        if konflikty:
            opis_k = "; ".join(f"{k.pakiet_a}↔{k.pakiet_b}" for k in konflikty)
            problemy.append(f"Konflikty licencji: {opis_k}")

        if strict:
            slabe = wynik.filtruj_po_ryzyku(PoziomRyzyka.SLABE_COPYLEFT)
            nieznane = wynik.filtruj_po_ryzyku(PoziomRyzyka.NIEZNANA)
            if slabe:
                nazwy = ", ".join(a.zaleznosc.nazwa for a in slabe)
                problemy.append(f"Licencje słabego copyleft (--strict): {nazwy}")
            if nieznane:
                nazwy = ", ".join(a.zaleznosc.nazwa for a in nieznane)
                problemy.append(f"Nieznane licencje (--strict): {nazwy}")

        if problemy:
            click.echo("\n❌ AUDYT LICENCJI NIEUDANY — wykryto problemy:", err=True)
            for problem in problemy:
                click.echo(f"   • {problem}", err=True)
            click.echo(
                "\nZatrzymano merge. Napraw problemy licencyjne przed kontynuowaniem.",
                err=True,
            )
            sys.exit(1)
        else:
            if not quiet:
                click.echo("\n✅ Audyt licencji zakończony pomyślnie — brak problemów.")


if __name__ == "__main__":
    cli()
