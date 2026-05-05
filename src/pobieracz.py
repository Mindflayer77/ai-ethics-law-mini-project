"""
Pobieranie informacji o licencjach pakietów z rejestrów PyPI i npm.

Implementacja:
- PyPI JSON API: https://pypi.org/pypi/{package}/json
- npm Registry API: https://registry.npmjs.org/{package}

Wyniki są buforowane lokalnie w pliku JSON (.cache/licencje_cache.json)
przez 24 godziny, aby uniknąć nadmiernego obciążania zewnętrznych API.

Bezpieczeństwo:
- Nie przechowuje kluczy API
- Nie loguje pełnych odpowiedzi HTTP
- Weryfikuje format nazw pakietów przed wysłaniem zapytania
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
from loguru import logger

# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

# Czas ważności cache w sekundach (24 godziny)
_CACHE_TTL = 24 * 60 * 60

# Timeout dla żądań HTTP (sekundy)
_HTTP_TIMEOUT = 10

# Ścieżka pliku cache (tworzona automatycznie)
_CACHE_SCIEZKA = Path(".cache") / "licencje_cache.json"

# Nagłówek User-Agent — dobre praktyki przy korzystaniu z publicznych API
_USER_AGENT = "ai-ethics-license-auditor/1.0 (PWr mini-projekt; https://github.com)"

# Wzorzec bezpiecznej nazwy pakietu (alfanumeryczne, myślniki, podkreślenia, kropki)
_BEZPIECZNA_NAZWA = re.compile(r"^[A-Za-z0-9._-]+$")

# ---------------------------------------------------------------------------
# Ręczne mapowanie licencji dla pakietów, których licencja nie jest dostępna
# przez API PyPI/npm (zweryfikowano ręcznie przez repozytoria GitHub lub
# oficjalne strony projektów — maj 2025)
# ---------------------------------------------------------------------------
_ZNANE_LICENCJE_FALLBACK: dict[str, str] = {
    # PyPI
    "pypi:amdsmi": "MIT",            # https://github.com/ROCm/amdsmi — MIT License
    "pypi:azure-core": "MIT",        # https://github.com/Azure/azure-sdk-for-python — MIT License
    "pypi:crewai": "MIT",            # https://github.com/crewAIInc/crewAI — MIT License
    "pypi:kaleido": "MIT",           # https://github.com/plotly/Kaleido — MIT License
    "pypi:needlehaystack": "MIT",    # https://github.com/gkamradt/LLMTest_NeedleInAHaystack — MIT License
    "pypi:sentencepiece": "Apache-2.0",  # https://github.com/google/sentencepiece — Apache 2.0
    # npm
    "npm:@ast-grep/cli": "MIT",           # https://github.com/ast-grep/ast-grep — MIT
    "npm:@next/plugin-storybook": "MIT",  # https://github.com/vercel/next.js — MIT
    "npm:@next/rspack-binding": "MIT",    # https://github.com/vercel/next.js — MIT
    "npm:@next/rspack-core": "MIT",       # https://github.com/vercel/next.js — MIT
    "npm:@pandacss/dev": "MIT",           # npm registry — MIT
    "npm:@prisma/extension-accelerate": "Apache-2.0",  # https://github.com/prisma/prisma — Apache-2.0
    "npm:busboy": "MIT",                  # https://github.com/mscdex/busboy — MIT
    "npm:expect.js": "MIT",              # https://github.com/Automattic/expect.js — MIT
    "npm:ignore-loader": "MIT",          # https://github.com/cherrry/ignore-loader — MIT
    "npm:isomorphic-unfetch": "MIT",     # npm registry — MIT
    "npm:next-rspack": "MIT",            # https://github.com/vercel/next.js — MIT
    "npm:next-seo": "MIT",              # https://github.com/garmeeh/next-seo — MIT
    "npm:passport-local": "MIT",        # https://github.com/jaredhanson/passport-local — MIT
    "npm:pixrem": "MIT",                # https://github.com/robwierzbowski/node-pixrem — MIT
    "npm:prettier-plugin-tailwindcss": "MIT",  # npm registry — MIT
    "npm:querystring-es3": "MIT",       # https://github.com/Gozala/querystring — MIT
    "npm:mailgun": "Apache-2.0",        # https://github.com/mailgun/mailgun-js — Apache-2.0
}


# ---------------------------------------------------------------------------
# Struktury danych
# ---------------------------------------------------------------------------


@dataclass
class WynikPobierania:
    """Wynik pobrania informacji o licencji pakietu."""

    nazwa: str
    wersja: str | None
    ekosystem: str
    licencja_surowa: str | None
    url_zrodla: str
    blad: str | None = None

    @property
    def sukces(self) -> bool:
        """Czy pobieranie zakończyło się sukcesem."""
        return self.blad is None


# ---------------------------------------------------------------------------
# Zarządzanie cache
# ---------------------------------------------------------------------------


def _wczytaj_cache() -> dict:
    """Wczytuje cache z pliku JSON. Zwraca pusty słownik jeśli brak pliku."""
    if not _CACHE_SCIEZKA.exists():
        return {}
    try:
        return json.loads(_CACHE_SCIEZKA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _zapisz_cache(dane: dict) -> None:
    """Zapisuje cache do pliku JSON, pomijając przeterminowane wpisy."""
    teraz = time.time()
    dane_aktualne = {
        klucz: wpis
        for klucz, wpis in dane.items()
        if teraz - wpis.get("_czas", 0) <= _CACHE_TTL
    }
    try:
        _CACHE_SCIEZKA.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_SCIEZKA.write_text(
            json.dumps(dane_aktualne, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as blad:
        logger.warning("Nie można zapisać cache: {}", blad)


def _klucz_cache(nazwa: str, ekosystem: str) -> str:
    """Tworzy klucz cache dla pakietu."""
    return f"{ekosystem}:{nazwa.lower()}"


def _pobierz_z_cache(
    cache: dict, klucz: str
) -> dict | None:
    """
    Pobiera wpis z cache jeśli nie jest przestarzały.

    Returns:
        Dane wpisu lub None jeśli brak / przestarzały.
    """
    wpis = cache.get(klucz)
    if not wpis:
        return None
    czas_zapisu = wpis.get("_czas", 0)
    if time.time() - czas_zapisu > _CACHE_TTL:
        return None
    return wpis


# ---------------------------------------------------------------------------
# Pobieranie z PyPI
# ---------------------------------------------------------------------------


def pobierz_licencje_pypi(nazwa: str, wersja: str | None = None) -> WynikPobierania:
    """
    Pobiera informacje o licencji pakietu Python z PyPI JSON API.

    Args:
        nazwa: Nazwa pakietu (np. "requests", "numpy").
        wersja: Opcjonalna konkretna wersja (np. "2.31.0").

    Returns:
        WynikPobierania z surową nazwą licencji lub błędem.
    """
    if not _waliduj_nazwe_pakietu(nazwa):
        return WynikPobierania(
            nazwa=nazwa,
            wersja=wersja,
            ekosystem="pypi",
            licencja_surowa=None,
            url_zrodla="",
            blad=f"Nieprawidłowa nazwa pakietu: {nazwa!r}",
        )

    cache = _wczytaj_cache()
    klucz = _klucz_cache(nazwa, "pypi")
    cached = _pobierz_z_cache(cache, klucz)
    if cached:
        logger.debug("Cache hit: {}", klucz)
        return WynikPobierania(
            nazwa=cached["nazwa"],
            wersja=cached.get("wersja"),
            ekosystem="pypi",
            licencja_surowa=cached.get("licencja_surowa"),
            url_zrodla=cached.get("url_zrodla", ""),
        )

    # Buduj URL — używamy bezpiecznej nazwy (walidowanej powyżej)
    if wersja:
        url = f"https://pypi.org/pypi/{nazwa}/{wersja}/json"
    else:
        url = f"https://pypi.org/pypi/{nazwa}/json"

    logger.debug("Pobieranie PyPI: {}", url)
    try:
        odpowiedz = requests.get(
            url,
            timeout=_HTTP_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        )
        odpowiedz.raise_for_status()
        dane = odpowiedz.json()
    except requests.exceptions.HTTPError as blad:
        if blad.response is not None and blad.response.status_code == 404:
            msg = f"Pakiet '{nazwa}' nie znaleziony na PyPI"
        else:
            msg = f"Błąd HTTP: {blad}"
        logger.warning("PyPI {}: {}", nazwa, msg)
        return WynikPobierania(
            nazwa=nazwa,
            wersja=wersja,
            ekosystem="pypi",
            licencja_surowa=None,
            url_zrodla=url,
            blad=msg,
        )
    except requests.exceptions.RequestException as blad:
        msg = f"Błąd sieci: {blad}"
        logger.warning("PyPI {}: {}", nazwa, msg)
        return WynikPobierania(
            nazwa=nazwa,
            wersja=wersja,
            ekosystem="pypi",
            licencja_surowa=None,
            url_zrodla=url,
            blad=msg,
        )

    # Parsuj odpowiedź
    info = dane.get("info", {})
    licencja = _wyciagnij_licencje_pypi(info)
    # Fallback dla pakietów z brakiem danych w rejestrze
    if not licencja:
        licencja = _ZNANE_LICENCJE_FALLBACK.get(f"pypi:{nazwa.lower()}")
    aktualna_wersja = info.get("version")

    wynik = WynikPobierania(
        nazwa=nazwa,
        wersja=aktualna_wersja,
        ekosystem="pypi",
        licencja_surowa=licencja,
        url_zrodla=f"https://pypi.org/pypi/{nazwa}/json",
    )

    # Zapisz do cache
    cache[klucz] = {
        "nazwa": nazwa,
        "wersja": aktualna_wersja,
        "licencja_surowa": licencja,
        "url_zrodla": wynik.url_zrodla,
        "_czas": time.time(),
    }
    _zapisz_cache(cache)

    return wynik


def _wyciagnij_licencje_pypi(info: dict) -> str | None:
    """
    Wyciąga informację o licencji z metadanych PyPI.

    Sprawdza w kolejności:
    1. Pole "license_expression" (PEP 639 — SPDX expression, nowsze pakiety)
    2. Pole "license" (bezpośredni tekst licencji)
    3. Klasyfikatory PyPI zaczynające się od "License ::"
    """
    # 1. PEP 639: license_expression (SPDX identyfikator)
    lic_expr = info.get("license_expression") or ""
    if lic_expr and lic_expr.upper() not in ("UNKNOWN", "", "NONE"):
        # SPDX expression może być np. "MIT" lub "MIT AND Apache-2.0"
        # Weź pierwszą część (przed AND/OR)
        pierwsza = lic_expr.split(" ")[0].strip().rstrip(";")
        if pierwsza:
            return pierwsza

    # 2. Pole license
    licencja = info.get("license") or ""
    if licencja and licencja.upper() not in ("UNKNOWN", "", "NONE"):
        if len(licencja) < 100:
            return licencja.strip()
        else:
            # Długi tekst licencji — wyciągnij nazwę z pierwszych 120 znaków
            poczatek = licencja[:120].upper()
            if "MIT" in poczatek:
                return "MIT"
            elif "APACHE" in poczatek:
                return "Apache-2.0"
            elif "BSD" in poczatek:
                return "BSD-3-Clause"
            elif "LGPL" in poczatek:
                return "LGPL-3.0-only"
            elif "GPL" in poczatek:
                return "GPL-3.0-only"
            elif "MOZILLA" in poczatek or "MPL" in poczatek:
                return "MPL-2.0"

    # 3. Klasyfikatory
    klasyfikatory: list[str] = info.get("classifiers", []) or []
    for klas in klasyfikatory:
        if klas.startswith("License ::"):
            czesci = [c.strip() for c in klas.split("::")]
            if len(czesci) >= 3:
                # Zwróć ostatnią, najbardziej szczegółową część
                return czesci[-1]

    return None


# ---------------------------------------------------------------------------
# Pobieranie z npm
# ---------------------------------------------------------------------------


def pobierz_licencje_npm(nazwa: str, wersja: str | None = None) -> WynikPobierania:
    """
    Pobiera informacje o licencji pakietu Node.js z npm Registry.

    Args:
        nazwa: Nazwa pakietu (np. "express", "@types/node").
        wersja: Opcjonalna konkretna wersja.

    Returns:
        WynikPobierania z surową nazwą licencji lub błędem.
    """
    # Scoped packages (@scope/name) są dozwolone — sprawdź osobno
    if not _waliduj_nazwe_pakietu_npm(nazwa):
        return WynikPobierania(
            nazwa=nazwa,
            wersja=wersja,
            ekosystem="npm",
            licencja_surowa=None,
            url_zrodla="",
            blad=f"Nieprawidłowa nazwa pakietu npm: {nazwa!r}",
        )

    cache = _wczytaj_cache()
    klucz = _klucz_cache(nazwa, "npm")
    cached = _pobierz_z_cache(cache, klucz)
    if cached:
        logger.debug("Cache hit: {}", klucz)
        return WynikPobierania(
            nazwa=cached["nazwa"],
            wersja=cached.get("wersja"),
            ekosystem="npm",
            licencja_surowa=cached.get("licencja_surowa"),
            url_zrodla=cached.get("url_zrodla", ""),
        )

    # Zakoduj scoped packages (@ → %40, / → %2F) — tylko dla URL
    nazwa_zakodowana = nazwa.replace("/", "%2F")
    if wersja:
        url = f"https://registry.npmjs.org/{nazwa_zakodowana}/{wersja}"
    else:
        url = f"https://registry.npmjs.org/{nazwa_zakodowana}/latest"

    logger.debug("Pobieranie npm: {}", url)
    try:
        odpowiedz = requests.get(
            url,
            timeout=_HTTP_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        )
        odpowiedz.raise_for_status()
        dane = odpowiedz.json()
    except requests.exceptions.HTTPError as blad:
        if blad.response is not None and blad.response.status_code == 404:
            msg = f"Pakiet '{nazwa}' nie znaleziony na npm"
        else:
            msg = f"Błąd HTTP: {blad}"
        logger.warning("npm {}: {}", nazwa, msg)
        return WynikPobierania(
            nazwa=nazwa,
            wersja=wersja,
            ekosystem="npm",
            licencja_surowa=None,
            url_zrodla=url,
            blad=msg,
        )
    except requests.exceptions.RequestException as blad:
        msg = f"Błąd sieci: {blad}"
        logger.warning("npm {}: {}", nazwa, msg)
        return WynikPobierania(
            nazwa=nazwa,
            wersja=wersja,
            ekosystem="npm",
            licencja_surowa=None,
            url_zrodla=url,
            blad=msg,
        )

    licencja = _wyciagnij_licencje_npm(dane)
    # Fallback dla pakietów z brakiem danych w rejestrze
    if not licencja:
        licencja = _ZNANE_LICENCJE_FALLBACK.get(f"npm:{nazwa.lower()}")
    aktualna_wersja = dane.get("version")

    wynik = WynikPobierania(
        nazwa=nazwa,
        wersja=aktualna_wersja,
        ekosystem="npm",
        licencja_surowa=licencja,
        url_zrodla=f"https://www.npmjs.com/package/{nazwa}",
    )

    cache[klucz] = {
        "nazwa": nazwa,
        "wersja": aktualna_wersja,
        "licencja_surowa": licencja,
        "url_zrodla": wynik.url_zrodla,
        "_czas": time.time(),
    }
    _zapisz_cache(cache)

    return wynik


def _wyciagnij_licencje_npm(dane: dict) -> str | None:
    """Wyciąga informację o licencji z odpowiedzi npm Registry."""
    licencja = dane.get("license")
    if isinstance(licencja, str):
        return licencja.strip() or None
    if isinstance(licencja, dict):
        # Stary format: {"type": "MIT", "url": "..."}
        return licencja.get("type") or None
    # Stary format npm: tablica "licenses": [{"type": "MIT", "url": "..."}]
    licenses_arr = dane.get("licenses")
    if isinstance(licenses_arr, list) and licenses_arr:
        typ = licenses_arr[0].get("type") if isinstance(licenses_arr[0], dict) else None
        if typ:
            return typ.strip() or None
    return None


# ---------------------------------------------------------------------------
# Funkcja główna — pobieranie dla dowolnego ekosystemu
# ---------------------------------------------------------------------------


def pobierz_licencje(nazwa: str, ekosystem: str, wersja: str | None = None) -> WynikPobierania:
    """
    Pobiera informacje o licencji pakietu z odpowiedniego rejestru.

    Args:
        nazwa: Nazwa pakietu.
        ekosystem: "pypi" lub "npm".
        wersja: Opcjonalna wersja.

    Returns:
        WynikPobierania.
    """
    if ekosystem == "pypi":
        return pobierz_licencje_pypi(nazwa, wersja)
    elif ekosystem == "npm":
        return pobierz_licencje_npm(nazwa, wersja)
    else:
        return WynikPobierania(
            nazwa=nazwa,
            wersja=wersja,
            ekosystem=ekosystem,
            licencja_surowa=None,
            url_zrodla="",
            blad=f"Nieobsługiwany ekosystem: {ekosystem!r}",
        )


def pobierz_licencje_batch(
    zaleznie: list,  # list[Zaleznosc]
    opoznienie: float = 0.1,
) -> list[WynikPobierania]:
    """
    Pobiera licencje dla listy zależności z krótkim opóźnieniem między zapytaniami.

    Args:
        zaleznie: Lista obiektów Zaleznosc.
        opoznienie: Opóźnienie w sekundach między zapytaniami (domyślnie 0.1s).

    Returns:
        Lista WynikPobierania w tej samej kolejności.
    """
    wyniki = []
    for i, dep in enumerate(zaleznie):
        logger.info("[{}/{}] Pobieranie: {} ({})", i + 1, len(zaleznie), dep.nazwa, dep.ekosystem)
        wynik = pobierz_licencje(dep.nazwa, dep.ekosystem, dep.wersja)
        wyniki.append(wynik)
        if i < len(zaleznie) - 1:
            time.sleep(opoznienie)
    return wyniki


# ---------------------------------------------------------------------------
# Walidacja nazw pakietów (bezpieczeństwo: zapobieganie path traversal)
# ---------------------------------------------------------------------------


def _waliduj_nazwe_pakietu(nazwa: str) -> bool:
    """
    Waliduje nazwę pakietu Python (PyPI).
    Dozwolone znaki: litery, cyfry, myślniki, podkreślenia, kropki.
    """
    if not nazwa or len(nazwa) > 200:
        return False
    return bool(_BEZPIECZNA_NAZWA.match(nazwa))


def _waliduj_nazwe_pakietu_npm(nazwa: str) -> bool:
    """
    Waliduje nazwę pakietu npm.
    Obsługuje scoped packages (@scope/name).
    """
    if not nazwa or len(nazwa) > 214:
        return False
    if nazwa.startswith("@"):
        # Scoped: @scope/name
        wzorzec = re.compile(r"^@[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")
        return bool(wzorzec.match(nazwa))
    return bool(_BEZPIECZNA_NAZWA.match(nazwa))
