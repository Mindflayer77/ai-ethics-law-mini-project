"""
Silnik analizy licencji zależności.

Łączy wyniki skanowania (Zaleznosc) z informacjami o licencjach
(WynikPobierania) i klasyfikuje każdą zależność według poziomu ryzyka prawnego.

Wykrywa konflikty kompatybilności między licencjami w projekcie.
Generuje podsumowanie statystyczne i rekomendacje.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from licencje import (
    LicencjaInfo,
    PoziomRyzyka,
    ZNANE_LICENCJE,
    normalizuj_nazwe_licencji,
    pobierz_info_licencji,
    sprawdz_niekompatybilnosc,
)
from pobieracz import WynikPobierania
from skaner import Zaleznosc


# ---------------------------------------------------------------------------
# Struktury danych wyników analizy
# ---------------------------------------------------------------------------


@dataclass
class ZaleznoscAnaliza:
    """Wynik analizy pojedynczej zależności."""

    zaleznosc: Zaleznosc
    wynik_pobierania: WynikPobierania
    licencja_spdx: str | None
    info_licencji: LicencjaInfo | None

    @property
    def poziom_ryzyka(self) -> PoziomRyzyka:
        """Poziom ryzyka prawnego tej zależności."""
        if self.info_licencji:
            return self.info_licencji.poziom_ryzyka
        if self.wynik_pobierania.blad:
            return PoziomRyzyka.NIEZNANA
        if not self.licencja_spdx:
            return PoziomRyzyka.NIEZNANA
        # Nierozpoznana nazwa licencji — zakładamy nieznany poziom
        return PoziomRyzyka.NIEZNANA

    @property
    def opis_licencji(self) -> str:
        """Opis licencji lub informacja o braku danych."""
        if self.info_licencji:
            return self.info_licencji.opis
        if self.wynik_pobierania.blad:
            return f"Błąd pobierania: {self.wynik_pobierania.blad}"
        if not self.licencja_spdx:
            return "Brak informacji o licencji. Wymaga ręcznej weryfikacji."
        return f"Licencja '{self.licencja_spdx}' nie jest w bazie danych — weryfikuj ręcznie."

    @property
    def nazwa_licencji_do_wyswietlenia(self) -> str:
        """Czytelna nazwa licencji do wyświetlenia."""
        if self.info_licencji:
            return self.info_licencji.spdx_id
        if self.wynik_pobierania.licencja_surowa:
            return self.wynik_pobierania.licencja_surowa
        return "Nieznana"


@dataclass
class KonfliktLicencji:
    """Wykryty konflikt kompatybilności między dwiema zależnościami."""

    pakiet_a: str
    licencja_a: str
    pakiet_b: str
    licencja_b: str
    opis: str


@dataclass
class WynikAnalizy:
    """Kompletny wynik analizy projektu."""

    zaleznie_analizy: list[ZaleznoscAnaliza]
    konflikty: list[KonfliktLicencji]

    @property
    def liczba_zaleznie(self) -> int:
        return len(self.zaleznie_analizy)

    @property
    def statystyki_ryzyka(self) -> dict[PoziomRyzyka, int]:
        """Liczba zależności per poziom ryzyka."""
        stats: dict[PoziomRyzyka, int] = {p: 0 for p in PoziomRyzyka}
        for z in self.zaleznie_analizy:
            stats[z.poziom_ryzyka] += 1
        return stats

    @property
    def procenty_ryzyka(self) -> dict[PoziomRyzyka, float]:
        """Procent zależności per poziom ryzyka."""
        stats = self.statystyki_ryzyka
        total = self.liczba_zaleznie or 1
        return {p: round(v / total * 100, 1) for p, v in stats.items()}

    @property
    def ma_wysokie_ryzyko(self) -> bool:
        """Czy projekt zawiera licencje silnego copyleft lub własnościowe."""
        stats = self.statystyki_ryzyka
        return (
            stats[PoziomRyzyka.SILNE_COPYLEFT] > 0
            or stats[PoziomRyzyka.WLASNOSCI] > 0
        )

    @property
    def ma_nieznane_licencje(self) -> bool:
        """Czy projekt zawiera zależności bez informacji o licencji."""
        return self.statystyki_ryzyka[PoziomRyzyka.NIEZNANA] > 0

    def filtruj_po_ryzyku(self, poziom: PoziomRyzyka) -> list[ZaleznoscAnaliza]:
        """Zwraca zależności z danym poziomem ryzyka."""
        return [z for z in self.zaleznie_analizy if z.poziom_ryzyka == poziom]


# ---------------------------------------------------------------------------
# Główna funkcja analizy
# ---------------------------------------------------------------------------


def analizuj_zaleznie(
    zaleznie: list[Zaleznosc],
    wyniki_pobierania: list[WynikPobierania],
) -> WynikAnalizy:
    """
    Analizuje zależności projektu — klasyfikuje licencje i wykrywa konflikty.

    Args:
        zaleznie: Lista zależności z pliku manifestu.
        wyniki_pobierania: Lista wyników pobierania informacji o licencjach.

    Returns:
        WynikAnalizy z pełną analizą projektu.
    """
    if len(zaleznie) != len(wyniki_pobierania):
        raise ValueError(
            f"Niezgodna liczba zależności ({len(zaleznie)}) "
            f"i wyników pobierania ({len(wyniki_pobierania)})"
        )

    analizy: list[ZaleznoscAnaliza] = []

    for dep, wynik in zip(zaleznie, wyniki_pobierania):
        analiza = _analizuj_pojedyncza(dep, wynik)
        analizy.append(analiza)

    konflikty = _wykryj_konflikty(analizy)

    return WynikAnalizy(zaleznie_analizy=analizy, konflikty=konflikty)


def _analizuj_pojedyncza(
    dep: Zaleznosc, wynik: WynikPobierania
) -> ZaleznoscAnaliza:
    """
    Klasyfikuje pojedynczą zależność.

    Próbuje dopasować surową nazwę licencji do bazy SPDX.
    """
    licencja_spdx: str | None = None
    info: LicencjaInfo | None = None

    if wynik.licencja_surowa:
        # Próba normalizacji do SPDX
        licencja_spdx = normalizuj_nazwe_licencji(wynik.licencja_surowa)
        if licencja_spdx:
            info = pobierz_info_licencji(licencja_spdx)
            if not info:
                logger.debug(
                    "Brak info dla SPDX '{}' (pakiet: {})",
                    licencja_spdx,
                    dep.nazwa,
                )
        else:
            # Nie udało się znormalizować — sprawdź czy to klasyfikator PyPI
            licencja_spdx = _parsuj_klasyfikator_pypi(wynik.licencja_surowa)
            if licencja_spdx:
                info = pobierz_info_licencji(licencja_spdx)
            else:
                logger.debug(
                    "Nie można znormalizować licencji '{}' dla pakietu {}",
                    wynik.licencja_surowa,
                    dep.nazwa,
                )

    return ZaleznoscAnaliza(
        zaleznosc=dep,
        wynik_pobierania=wynik,
        licencja_spdx=licencja_spdx,
        info_licencji=info,
    )


def _parsuj_klasyfikator_pypi(klasyfikator: str) -> str | None:
    """
    Parsuje klasyfikator PyPI w formacie "License :: OSI Approved :: MIT License".
    Zwraca SPDX ID lub None.
    """
    if "::" not in klasyfikator:
        return None
    czesci = [c.strip() for c in klasyfikator.split("::")]
    if not czesci or czesci[0].lower() != "license":
        return None
    # Weź ostatnią część (najbardziej szczegółową)
    nazwa = czesci[-1]
    return normalizuj_nazwe_licencji(nazwa)


# ---------------------------------------------------------------------------
# Wykrywanie konfliktów kompatybilności
# ---------------------------------------------------------------------------


def _wykryj_konflikty(analizy: list[ZaleznoscAnaliza]) -> list[KonfliktLicencji]:
    """
    Sprawdza pary licencji w projekcie pod kątem niekompatybilności.

    Analizuje tylko zależności z rozpoznanymi SPDX ID.
    """
    konflikty: list[KonfliktLicencji] = []

    # Zbierz zależności z rozpoznanymi licencjami
    z_licencja = [
        (a.zaleznosc.nazwa, a.licencja_spdx)
        for a in analizy
        if a.licencja_spdx
    ]

    # Sprawdź każdą unikalną parę
    widziane_pary: set[tuple[str, str]] = set()
    for i, (pkg_a, lic_a) in enumerate(z_licencja):
        for pkg_b, lic_b in z_licencja[i + 1 :]:
            if (lic_a, lic_b) in widziane_pary or (lic_b, lic_a) in widziane_pary:
                continue
            widziane_pary.add((lic_a, lic_b))

            powod = sprawdz_niekompatybilnosc(lic_a, lic_b)
            if powod:
                konflikty.append(
                    KonfliktLicencji(
                        pakiet_a=pkg_a,
                        licencja_a=lic_a,
                        pakiet_b=pkg_b,
                        licencja_b=lic_b,
                        opis=powod,
                    )
                )
                logger.warning(
                    "Konflikt licencji: {} ({}) ↔ {} ({})",
                    pkg_a,
                    lic_a,
                    pkg_b,
                    lic_b,
                )

    return konflikty


# ---------------------------------------------------------------------------
# Generowanie rekomendacji
# ---------------------------------------------------------------------------


def generuj_rekomendacje(wynik: WynikAnalizy) -> list[str]:
    """
    Generuje listę konkretnych rekomendacji na podstawie wyników analizy.

    Rekomendacje są oparte na rzeczywistych wymaganiach prawnych
    licencji open-source i mają formę actionable steps.

    Returns:
        Lista rekomendacji w kolejności priorytetu.
    """
    rekomendacje: list[str] = []
    stats = wynik.statystyki_ryzyka

    # 1. Licencje silnego copyleft
    silne_copyleft = wynik.filtruj_po_ryzyku(PoziomRyzyka.SILNE_COPYLEFT)
    agpl = [z for z in silne_copyleft if z.licencja_spdx and "AGPL" in z.licencja_spdx]
    gpl = [z for z in silne_copyleft if z.licencja_spdx and "GPL" in (z.licencja_spdx or "") and "AGPL" not in (z.licencja_spdx or "")]
    saas_copyleft = [
        z for z in wynik.zaleznie_analizy 
        if z.info_licencji and z.info_licencji.uzytkowan_sieciowe_wyzwala_copyleft
    ]
    if saas_copyleft:
        nazwy = ", ".join(set(z.zaleznosc.nazwa for z in saas_copyleft))
        rekomendacje.append(
            f"⛔ KRYTYCZNE — Copyleft Sieciowy (SaaS): Pakiety [{nazwy}] posiadają licencję wymagającą udostępnienia kodu przez sieć (np. AGPL-3.0 lub EUPL-1.2). "
            "Jeśli udostępniasz ten projekt jako publiczną usługę sieciową (SaaS/API/Web), "
            "MUSISZ udostępnić pełny kod źródłowy użytkownikom. "
            "Rozważ: (a) otwarcie projektu, (b) zakup licencji komercyjnej od autorów, (c) wymianę pakietów."
        )

    gpl_only = [
        z for z in silne_copyleft 
        if z.info_licencji and not z.info_licencji.uzytkowan_sieciowe_wyzwala_copyleft
    ]
    if gpl_only:
        nazwy = ", ".join(set(z.zaleznosc.nazwa for z in gpl_only))
        rekomendacje.append(
            f"⚠️ WYSOKIE RYZYKO — Silne Copyleft (GPL): Pakiety [{nazwy}] wymagają, by projekt je dołączający był wydany na tej samej licencji. "
            "Nie można dystrybuować oprogramowania zamkniętego komercyjnego (binariów/aplikacji) połączonego z tym kodem."
        )
         
    if wynik.konflikty:
        for konflikt in wynik.konflikty:
            rekomendacje.append(
                f"⚠️ KONFLIKT LICENCJI: {konflikt.pakiet_a} ({konflikt.licencja_a}) "
                f"↔ {konflikt.pakiet_b} ({konflikt.licencja_b}). "
                f"{konflikt.opis} "
                "Skonsultuj się z prawnikiem przed dystrybucją projektu."
            )

    # 2. Konflikty kompatybilności
    if wynik.konflikty:
        for konflikt in wynik.konflikty:
            rekomendacje.append(
                f"⚠️ KONFLIKT LICENCJI: {konflikt.pakiet_a} ({konflikt.licencja_a}) "
                f"↔ {konflikt.pakiet_b} ({konflikt.licencja_b}). "
                f"{konflikt.opis} "
                "Skonsultuj się z prawnikiem przed dystrybucją projektu."
            )

    # 3. Nieznane licencje
    nieznane = wynik.filtruj_po_ryzyku(PoziomRyzyka.NIEZNANA)
    if nieznane:
        nazwy = ", ".join(z.zaleznosc.nazwa for z in nieznane[:5])
        pozostale = max(0, len(nieznane) - 5)
        suf = f" i {pozostale} więcej" if pozostale else ""
        rekomendacje.append(
            f"❓ NIEZNANA LICENCJA: Pakiety [{nazwy}{suf}] "
            "nie mają określonej licencji lub nie udało się jej pobrać. "
            "Sprawdź ręcznie: plik LICENSE/COPYING w repozytorium pakietu, "
            "lub stronę pakietu na PyPI/npm."
        )

    # 4. Własnościowe licencje
    wlasnosci = wynik.filtruj_po_ryzyku(PoziomRyzyka.WLASNOSCI)
    if wlasnosci:
        nazwy = ", ".join(z.zaleznosc.nazwa for z in wlasnosci)
        rekomendacje.append(
            f"🔒 LICENCJA WŁASNOŚCIOWA: Pakiety [{nazwy}] "
            "mają licencję własnościową/komercyjną. "
            "Sprawdź warunki użytkowania i upewnij się, "
            "że posiadasz odpowiednią licencję komercyjną."
        )

    # 5. Słabe copyleft — porada
    slabe_copyleft = wynik.filtruj_po_ryzyku(PoziomRyzyka.SLABE_COPYLEFT)
    lgpl_pkgs = [z for z in slabe_copyleft if z.licencja_spdx and "LGPL" in z.licencja_spdx]
    if lgpl_pkgs:
        nazwy = ", ".join(z.zaleznosc.nazwa for z in lgpl_pkgs[:3])
        rekomendacje.append(
            f"ℹ️ LGPL — LINKOWANIE DYNAMICZNE: Pakiety [{nazwy}] można używać w zamkniętych projektach, "
            "ale musisz upewnić się, że ładujesz je dynamicznie (np. poprzez importy w Pythonie/Node, biblioteki .dll/.so), "
            "oraz udostępnisz wprowadzane modyfikacje wewnątrz samego kodu tych bibliotek."
        )
        
    file_copyleft_pkgs = [z for z in slabe_copyleft if z.licencja_spdx and ("MPL" in z.licencja_spdx or "EPL" in z.licencja_spdx)]
    if file_copyleft_pkgs:
        nazwy = ", ".join(z.zaleznosc.nazwa for z in file_copyleft_pkgs[:3])
        rekomendacje.append(
            f"ℹ️ MPL/EPL — COPYLEFT NA POZIOMIE PLIKU: Pakiety [{nazwy}] pozwalają na swobodne mieszanie ich plików z kodem zamkniętym. "
            "Musisz jednak udostępnić kody źródłowe w przypadku jakiejkolwiek zmiany konkretnych plików objętych licencją MPL/EPL."
        )

    # 6. Jeśli wszystko OK
    if not (saas_copyleft or silne_copyleft or wlasnosci or wynik.konflikty):
        rekomendacje.append(
            "✅ Brak krytycznych problemów licencyjnych. Projekt korzysta z łagodnych licencji (Permissive). "
            "Pamiętaj jednak, że starsze licencje (np. MIT, BSD) mogą nie zawierać wyraźnej ochrony " # NOWE
            "przed roszczeniami patentowymi (w odróżnieniu od Apache-2.0)." # NOWE
        )
    else:
        rekomendacje.append(
            "📋 OGÓLNE: Zawsze dołączaj teksty licencji pakietów, z których korzystasz. " # NOWE
            "Dla Apache-2.0 zachowaj plik NOTICE. W przypadku BSD-3-Clause pamiętaj, " # NOWE
            "że zabronione jest używanie nazw twórców do reklamy Twojego projektu." # NOWE
        )

    return rekomendacje
