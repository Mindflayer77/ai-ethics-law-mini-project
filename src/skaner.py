"""
Skaner zależności projektu.

Obsługuje następujące formaty plików:
- requirements.txt (i warianty: requirements-dev.txt, requirements-test.txt itp.)
- pyproject.toml (PEP 517/518/621)
- package.json (Node.js/npm)
- setup.cfg
- Pipfile

Każda zależność jest reprezentowana przez obiekt Zaleznosc zawierający
nazwę pakietu, wersję (jeśli podana), ekosystem (pypi/npm) i plik źródłowy.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger


@dataclass
class Zaleznosc:
    """Reprezentuje jedną zależność projektu."""

    nazwa: str
    wersja: str | None
    ekosystem: str  # "pypi" lub "npm"
    plik_zrodlowy: str

    def __str__(self) -> str:
        wer = f"=={self.wersja}" if self.wersja else ""
        return f"{self.nazwa}{wer} ({self.ekosystem}, {self.plik_zrodlowy})"


def skanuj_projekt(sciezka_projektu: Path, maks_glebokosc: int | None = None) -> list[Zaleznosc]:
    """
    Skanuje katalog projektu w poszukiwaniu wszystkich zależności.

    Przeszukuje znane pliki manifestowe i zbiera z nich listy pakietów.
    Usuwa duplikaty (ta sama nazwa + ekosystem).

    Args:
        sciezka_projektu: Ścieżka do katalogu projektu.
        maks_glebokosc: Maksymalna głębokość skanowania (0 = tylko katalog główny,
            1 = jeden poziom podkatalogów, None = bez limitu).

    Returns:
        Lista unikalnych zależności.
    """
    if not sciezka_projektu.is_dir():
        raise ValueError(f"Podana ścieżka nie jest katalogiem: {sciezka_projektu}")

    wszystkie: list[Zaleznosc] = []

    # --- Python ---
    # pyproject.toml
    for plik in _szukaj_pliki(sciezka_projektu, "pyproject.toml", maks_glebokosc):
        if _pominij_sciezke(plik):
            continue
        logger.info("Skanowanie: {}", plik.relative_to(sciezka_projektu))
        wszystkie.extend(_skanuj_pyproject_toml(plik))

    # requirements*.txt
    for plik in sorted(_szukaj_pliki(sciezka_projektu, "requirements*.txt", maks_glebokosc)):
        if _pominij_sciezke(plik):
            continue
        logger.info("Skanowanie: {}", plik.relative_to(sciezka_projektu))
        wszystkie.extend(_skanuj_requirements_txt(plik))

    # setup.cfg
    for plik in _szukaj_pliki(sciezka_projektu, "setup.cfg", maks_glebokosc):
        if _pominij_sciezke(plik):
            continue
        logger.info("Skanowanie: {}", plik.relative_to(sciezka_projektu))
        wszystkie.extend(_skanuj_setup_cfg(plik))

    # Pipfile
    for plik in _szukaj_pliki(sciezka_projektu, "Pipfile", maks_glebokosc):
        if _pominij_sciezke(plik):
            continue
        logger.info("Skanowanie: {}", plik.relative_to(sciezka_projektu))
        wszystkie.extend(_skanuj_pipfile(plik))

    # --- Node.js ---
    for plik in _szukaj_pliki(sciezka_projektu, "package.json", maks_glebokosc):
        if _pominij_sciezke(plik):
            continue
        logger.info("Skanowanie: {}", plik.relative_to(sciezka_projektu))
        wszystkie.extend(_skanuj_package_json(plik))

    # Usuń duplikaty (ta sama nazwa + ekosystem)
    unikalne = _deduplikuj(wszystkie)
    logger.info("Znaleziono {} unikalnych zależności.", len(unikalne))
    return unikalne


# ---------------------------------------------------------------------------
# Parsery poszczególnych formatów
# ---------------------------------------------------------------------------


def _skanuj_requirements_txt(sciezka: Path) -> list[Zaleznosc]:
    """
    Parsuje plik requirements.txt.

    Obsługuje:
    - pakiet==wersja, pakiet>=wersja, pakiet~=wersja (pobiera tylko nazwę)
    - komentarze (#)
    - dyrektywy -r, -c (ignorowane)
    - URL-e i ścieżki lokalne (ignorowane)
    """
    wyniki: list[Zaleznosc] = []
    try:
        tekst = sciezka.read_text(encoding="utf-8", errors="replace")
    except OSError as blad:
        logger.warning("Nie można odczytać {}: {}", sciezka, blad)
        return wyniki

    for numer, linia in enumerate(tekst.splitlines(), start=1):
        linia = linia.strip()
        # Usuń komentarze inline
        if "#" in linia:
            linia = linia[: linia.index("#")].strip()
        if not linia or linia.startswith(("-r", "-c", "-i", "--", "http", "git+")):
            continue
        # Parsuj specyfikację zależności, np. numpy>=1.24, requests==2.31.0
        dopasowanie = re.match(r"^([A-Za-z0-9_.\-\[\]]+?)\s*([><=~!;].*)?$", linia)
        if dopasowanie:
            nazwa_surowa = dopasowanie.group(1)
            # Usuń extras z nawiasów kwadratowych, np. requests[security] → requests
            nazwa = re.sub(r"\[.*\]", "", nazwa_surowa).strip()
            if not nazwa:
                continue
            # Wyciągnij dokładną wersję jeśli podana jako ==X.Y.Z
            wersja = None
            specyfikator = dopasowanie.group(2) or ""
            dopasowanie_wer = re.search(r"==\s*([^\s,;]+)", specyfikator)
            if dopasowanie_wer:
                wersja = dopasowanie_wer.group(1)
            wyniki.append(
                Zaleznosc(
                    nazwa=nazwa,
                    wersja=wersja,
                    ekosystem="pypi",
                    plik_zrodlowy=str(sciezka),
                )
            )
        else:
            logger.debug("Linia {} w {} — nie można sparsować: {}", numer, sciezka.name, linia)

    return wyniki


def _skanuj_pyproject_toml(sciezka: Path) -> list[Zaleznosc]:
    """
    Parsuje plik pyproject.toml (PEP 517/518/621).

    Obsługuje:
    - [project] → dependencies = [...]
    - [project.optional-dependencies] → wszystkie grupy
    - [tool.poetry.dependencies]
    - [tool.poetry.dev-dependencies]
    """
    wyniki: list[Zaleznosc] = []
    try:
        dane = tomllib.loads(sciezka.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as blad:
        logger.warning("Nie można odczytać {}: {}", sciezka, blad)
        return wyniki

    plik_str = str(sciezka)

    def _dodaj_z_listy(lista: list[str]) -> None:
        for wpis in lista:
            if not isinstance(wpis, str):
                continue
            # PEP 508: "requests>=2.0; python_version>'3'"
            nazwa_surowa = re.split(r"[><=!;\s\[]", wpis)[0].strip()
            if not nazwa_surowa or nazwa_surowa.startswith("#"):
                continue
            wersja = None
            dopasowanie_wer = re.search(r"==\s*([^\s,;]+)", wpis)
            if dopasowanie_wer:
                wersja = dopasowanie_wer.group(1)
            wyniki.append(
                Zaleznosc(
                    nazwa=nazwa_surowa,
                    wersja=wersja,
                    ekosystem="pypi",
                    plik_zrodlowy=plik_str,
                )
            )

    # PEP 621
    projekt = dane.get("project", {})
    _dodaj_z_listy(projekt.get("dependencies", []))
    for grupa in projekt.get("optional-dependencies", {}).values():
        _dodaj_z_listy(lista=grupa)

    # Poetry
    tool = dane.get("tool", {})
    poetry = tool.get("poetry", {})
    for klucz in ("dependencies", "dev-dependencies", "group"):
        if klucz == "group":
            for _grupa_name, _grupa_dane in poetry.get("group", {}).items():
                _dodaj_z_listy(list(_grupa_dane.get("dependencies", {}).keys()))
        else:
            deps = poetry.get(klucz, {})
            if isinstance(deps, dict):
                for nazwa in deps:
                    if nazwa.lower() == "python":
                        continue
                    wyniki.append(
                        Zaleznosc(
                            nazwa=nazwa,
                            wersja=None,
                            ekosystem="pypi",
                            plik_zrodlowy=plik_str,
                        )
                    )

    return wyniki


def _skanuj_setup_cfg(sciezka: Path) -> list[Zaleznosc]:
    """
    Parsuje sekcję install_requires z pliku setup.cfg.
    """
    import configparser

    wyniki: list[Zaleznosc] = []
    parser = configparser.ConfigParser()
    try:
        parser.read(sciezka, encoding="utf-8")
    except (OSError, configparser.Error) as blad:
        logger.warning("Nie można odczytać {}: {}", sciezka, blad)
        return wyniki

    plik_str = str(sciezka)
    for sekcja in ("options", "options.extras_require"):
        if not parser.has_section(sekcja):
            continue
        for klucz, wartosc in parser.items(sekcja):
            if klucz != "install_requires" and sekcja != "options.extras_require":
                continue
            for linia in wartosc.splitlines():
                linia = linia.strip()
                if not linia or linia.startswith("#"):
                    continue
                nazwa = re.split(r"[><=!;\s\[]", linia)[0].strip()
                if nazwa:
                    wyniki.append(
                        Zaleznosc(
                            nazwa=nazwa,
                            wersja=None,
                            ekosystem="pypi",
                            plik_zrodlowy=plik_str,
                        )
                    )
    return wyniki


def _skanuj_pipfile(sciezka: Path) -> list[Zaleznosc]:
    """
    Parsuje pliki Pipfile (format TOML).
    """
    wyniki: list[Zaleznosc] = []
    try:
        dane = tomllib.loads(sciezka.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as blad:
        logger.warning("Nie można odczytać {}: {}", sciezka, blad)
        return wyniki

    plik_str = str(sciezka)
    for sekcja in ("packages", "dev-packages"):
        for nazwa, wartosc in dane.get(sekcja, {}).items():
            if nazwa.lower() == "python":
                continue
            wersja = None
            if isinstance(wartosc, str) and wartosc != "*":
                dopasowanie = re.search(r"==\s*([^\s,]+)", wartosc)
                if dopasowanie:
                    wersja = dopasowanie.group(1)
            wyniki.append(
                Zaleznosc(
                    nazwa=nazwa,
                    wersja=wersja,
                    ekosystem="pypi",
                    plik_zrodlowy=plik_str,
                )
            )
    return wyniki


def _skanuj_package_json(sciezka: Path) -> list[Zaleznosc]:
    """
    Parsuje plik package.json dla Node.js.

    Obsługuje sekcje: dependencies, devDependencies, peerDependencies.
    """
    import json

    wyniki: list[Zaleznosc] = []
    try:
        dane = json.loads(sciezka.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as blad:
        logger.warning("Nie można odczytać {}: {}", sciezka, blad)
        return wyniki

    plik_str = str(sciezka)
    for sekcja in ("dependencies", "devDependencies", "peerDependencies"):
        for nazwa, wersja_raw in dane.get(sekcja, {}).items():
            # Wyciągnij wersję, np. "^1.2.3" → "1.2.3"
            wersja = None
            if isinstance(wersja_raw, str):
                dopasowanie = re.search(r"(\d+\.\d+(?:\.\d+)?)", wersja_raw)
                if dopasowanie:
                    wersja = dopasowanie.group(1)
            wyniki.append(
                Zaleznosc(
                    nazwa=nazwa,
                    wersja=wersja,
                    ekosystem="npm",
                    plik_zrodlowy=plik_str,
                )
            )
    return wyniki


# ---------------------------------------------------------------------------
# Funkcje pomocnicze
# ---------------------------------------------------------------------------


def _szukaj_pliki(katalog: Path, wzorzec: str, maks_glebokosc: int | None) -> list[Path]:
    """
    Zwraca listę plików pasujących do wzorca, opcjonalnie ograniczoną głębokością.

    Args:
        katalog: Katalog startowy.
        wzorzec: Wzorzec glob (np. "package.json", "requirements*.txt").
        maks_glebokosc: Maksymalna głębokość podkatalogów (0 = tylko katalog główny,
            None = bez limitu).

    Returns:
        Lista pasujących ścieżek.
    """
    wyniki = []
    for sciezka in katalog.rglob(wzorzec):
        if maks_glebokosc is not None:
            # Głębokość = liczba katalogów między katalogiem startowym a plikiem
            wzgledna = sciezka.relative_to(katalog)
            glebokosc = len(wzgledna.parts) - 1  # -1 bo ostatni element to sam plik
            if glebokosc > maks_glebokosc:
                continue
        wyniki.append(sciezka)
    return wyniki


def _pominij_sciezke(sciezka: Path) -> bool:
    """
    Sprawdza czy ścieżka powinna być pominięta
    (np. node_modules, .venv, dist, build).
    """
    katalogi_do_pominiecia = {
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        "__pycache__",
        ".tox",
        "site-packages",
        ".git",
    }
    for czesc in sciezka.parts:
        if czesc in katalogi_do_pominiecia:
            return True
    return False


def _deduplikuj(zaleznie: list[Zaleznosc]) -> list[Zaleznosc]:
    """
    Usuwa duplikaty — zachowuje pierwsze wystąpienie każdej pary (nazwa, ekosystem).
    """
    widziane: set[tuple[str, str]] = set()
    wyniki: list[Zaleznosc] = []
    for dep in zaleznie:
        klucz = (dep.nazwa.lower(), dep.ekosystem)
        if klucz not in widziane:
            widziane.add(klucz)
            wyniki.append(dep)
    return wyniki
