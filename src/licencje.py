"""
Baza danych licencji open-source z klasyfikacją ryzyka prawnego.

Źródła informacji:
- https://choosealicense.com/appendix/
- https://spdx.org/licenses/
- https://www.tldrlegal.com/
- https://opensource.org/licenses
- https://www.gnu.org/licenses/license-compatibility.html

Klasyfikacja ryzyka:
- BEZPIECZNA (permissive): MIT, Apache-2.0, BSD, ISC — można używać w dowolnym projekcie
- SLABE_COPYLEFT: LGPL, MPL, EUPL — można używać, ale z pewnymi ograniczeniami
- SILNE_COPYLEFT: GPL, AGPL — projekt korzystający z nich musi być na tej samej licencji
- WLASNOSCI: licencje własnościowe/komercyjne — wymagają osobnego sprawdzenia
- NIEZNANA: brak informacji o licencji — wymaga weryfikacji
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PoziomRyzyka(Enum):
    """Poziom ryzyka prawnego licencji."""

    BEZPIECZNA = "bezpieczna"
    SLABE_COPYLEFT = "słabe_copyleft"
    SILNE_COPYLEFT = "silne_copyleft"
    WLASNOSCI = "własnościowa"
    NIEZNANA = "nieznana"

    @property
    def etykieta(self) -> str:
        """Czytelna etykieta poziomu ryzyka."""
        return {
            PoziomRyzyka.BEZPIECZNA: "Bezpieczna (permissive)",
            PoziomRyzyka.SLABE_COPYLEFT: "Słabe copyleft",
            PoziomRyzyka.SILNE_COPYLEFT: "Silne copyleft",
            PoziomRyzyka.WLASNOSCI: "Własnościowa",
            PoziomRyzyka.NIEZNANA: "Nieznana",
        }[self]

    @property
    def kolor_css(self) -> str:
        """Kolor HTML dla danego poziomu ryzyka."""
        return {
            PoziomRyzyka.BEZPIECZNA: "#2ecc71",
            PoziomRyzyka.SLABE_COPYLEFT: "#f39c12",
            PoziomRyzyka.SILNE_COPYLEFT: "#e74c3c",
            PoziomRyzyka.WLASNOSCI: "#9b59b6",
            PoziomRyzyka.NIEZNANA: "#95a5a6",
        }[self]

    @property
    def kolor_tla_css(self) -> str:
        """Kolor tła HTML dla danego poziomu ryzyka."""
        return {
            PoziomRyzyka.BEZPIECZNA: "#d5f5e3",
            PoziomRyzyka.SLABE_COPYLEFT: "#fef9e7",
            PoziomRyzyka.SILNE_COPYLEFT: "#fdedec",
            PoziomRyzyka.WLASNOSCI: "#f5eef8",
            PoziomRyzyka.NIEZNANA: "#f2f3f4",
        }[self]


@dataclass
class LicencjaInfo:
    """Szczegółowe informacje o licencji open-source."""

    spdx_id: str
    nazwa: str
    poziom_ryzyka: PoziomRyzyka
    opis: str
    wymaga_udostepnienia_kodu: bool
    zezwala_na_uzytkowan_komercyjne: bool
    wymaga_zachowania_informacji_autorskich: bool
    link_spdx: str
    uzytkowan_sieciowe_wyzwala_copyleft: bool = False
    aliasy: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.spdx_id} ({self.nazwa})"


# ---------------------------------------------------------------------------
# Baza znanych licencji
# ---------------------------------------------------------------------------
ZNANE_LICENCJE: dict[str, LicencjaInfo] = {
    # ===== LICENCJE PERMISSIVE (BEZPIECZNE) =====
    "MIT": LicencjaInfo(
        spdx_id="MIT",
        nazwa="MIT License",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Jedna z najbardziej popularnych i liberalnych licencji open-source. "
            "Pozwala na dowolne użycie, kopiowanie, modyfikowanie, łączenie, "
            "publikowanie, dystrybucję i sprzedaż oprogramowania bez ograniczeń, "
            "pod warunkiem zachowania informacji o prawach autorskich. "
            "W pełni kompatybilna z licencjami własnościowymi i GPL."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/MIT.html",
        aliasy=[
            "MIT License",
            "The MIT License",
            "MIT license",
            "Expat License",
        ],
    ),
    "Apache-2.0": LicencjaInfo(
        spdx_id="Apache-2.0",
        nazwa="Apache License 2.0",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Permissive licencja od Apache Software Foundation. "
            "Zawiera wyraźną klauzulę patentową chroniącą użytkowników przed "
            "roszczeniami patentowymi ze strony współtwórców. "
            "Wymaga zachowania informacji o zmianach w plikach. "
            "Kompatybilna z GPL-3.0, ale NIEKOMPATYBILNA z GPL-2.0-only "
            "ze względu na wymogi klauzuli patentowej."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/Apache-2.0.html",
        aliasy=[
            "Apache License 2.0",
            "Apache Software License 2.0",
            "Apache 2.0",
            "Apache2",
            "ASL 2",
            "Apache License, Version 2.0",
        ],
    ),
    "BSD-2-Clause": LicencjaInfo(
        spdx_id="BSD-2-Clause",
        nazwa="BSD 2-Clause \"Simplified\" License",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Uproszczona wersja licencji BSD z dwoma klauzulami. "
            "Pozwala na dystrybucję w formie kodu źródłowego i binarnej, "
            "pod warunkiem zachowania informacji o prawach autorskich "
            "i tekstu licencji. Jedna z najprostszych licencji open-source."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/BSD-2-Clause.html",
        aliasy=[
            "BSD-2-Clause",
            "BSD 2-Clause",
            "Simplified BSD",
            "FreeBSD",
            "The BSD License",
        ],
    ),
    "BSD-3-Clause": LicencjaInfo(
        spdx_id="BSD-3-Clause",
        nazwa="BSD 3-Clause \"New\" or \"Revised\" License",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Licencja BSD z trzema klauzulami. Podobna do BSD-2-Clause, "
            "ale dodaje zakaz używania nazwy projektu i autorów do promocji "
            "produktów pochodnych bez pisemnej zgody. Szeroko stosowana "
            "przez projekty akademickie i badawcze."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/BSD-3-Clause.html",
        aliasy=[
            "BSD-3-Clause",
            "BSD 3-Clause",
            "New BSD",
            "Revised BSD",
            "Modified BSD",
            "BSD License",
            "3-Clause BSD License",
        ],
    ),
    "ISC": LicencjaInfo(
        spdx_id="ISC",
        nazwa="ISC License",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Prosta, permissive licencja semantycznie równoważna z MIT, "
            "ale z krótszym tekstem. Stosowana głównie w projektach z "
            "ekosystemu Node.js/npm. Używana m.in. przez OpenBSD."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/ISC.html",
        aliasy=["ISC License", "ISC license"],
    ),
    "Unlicense": LicencjaInfo(
        spdx_id="Unlicense",
        nazwa="The Unlicense",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Licencja dedykująca oprogramowanie do domeny publicznej. "
            "Całkowicie rezygnuje z praw autorskich. Można robić z kodem "
            "absolutnie wszystko bez żadnych ograniczeń czy wymagań."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=False,
        link_spdx="https://spdx.org/licenses/Unlicense.html",
        aliasy=["The Unlicense", "unlicense"],
    ),
    "CC0-1.0": LicencjaInfo(
        spdx_id="CC0-1.0",
        nazwa="Creative Commons Zero v1.0 Universal",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Narzędzie Creative Commons dedykujące utwór do domeny publicznej. "
            "Autor rezygnuje ze wszystkich praw autorskich w maksymalnym "
            "dopuszczalnym przez prawo zakresie. Używana głównie dla danych "
            "i treści, nie typowo dla kodu."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=False,
        link_spdx="https://spdx.org/licenses/CC0-1.0.html",
        aliasy=["CC0", "CC0 1.0", "CC0-1.0"],
    ),
    "CC-BY-4.0": LicencjaInfo(
        spdx_id="CC-BY-4.0",
        nazwa="Creative Commons Attribution 4.0 International",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Permissive licencja Creative Commons wymagająca podania autora. "
            "Pozwala na dowolne użycie, modyfikację i dystrybucję — również komercyjną — "
            "pod warunkiem zachowania informacji o autorze i źródle. "
            "Zaprojektowana dla danych, treści i dokumentacji, NIE dla kodu — "
            "Creative Commons oficjalnie odradza jej stosowanie do oprogramowania. "
            "Powszechnie używana w pakietach npm zawierających dane (np. caniuse-lite). "
            "Nie nakłada wymogu copyleft na dzieła pochodne."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/CC-BY-4.0.html",
        aliasy=["CC-BY-4.0", "CC BY 4.0", "Creative Commons Attribution 4.0"],
    ),
    "PSF-2.0": LicencjaInfo(
        spdx_id="PSF-2.0",
        nazwa="Python Software Foundation License 2.0",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Licencja Python Software Foundation, używana dla samego "
            "interpretera Python i standardowej biblioteki. Permissive, "
            "kompatybilna z GPL. Pozwala na użycie w projektach własnościowych."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/PSF-2.0.html",
        aliasy=["PSF", "Python Software Foundation License", "PSFL", "PSF License"],
    ),
    "BSL-1.0": LicencjaInfo(
        spdx_id="BSL-1.0",
        nazwa="Boost Software License 1.0",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Prosta, permissive licencja od projektu Boost. "
            "Nie wymaga zachowania informacji o prawach autorskich "
            "w dystrybucjach binarnych. Używana szeroko w bibliotekach C++."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=False,
        link_spdx="https://spdx.org/licenses/BSL-1.0.html",
        aliasy=["Boost Software License", "BSL", "Boost"],
    ),
    "Zlib": LicencjaInfo(
        spdx_id="Zlib",
        nazwa="zlib License",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Prosta licencja permissive używana przez bibliotekę zlib. "
            "Pozwala na dowolne użycie pod warunkiem nieusuwania informacji "
            "o prawach autorskich i nietwierdzenia, że stworzono oryginalny kod."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/Zlib.html",
        aliasy=["zlib", "zlib/libpng", "zlib License"],
    ),
    "Artistic-2.0": LicencjaInfo(
        spdx_id="Artistic-2.0",
        nazwa="Artistic License 2.0",
        poziom_ryzyka=PoziomRyzyka.BEZPIECZNA,
        opis=(
            "Licencja używana w środowisku Perl. Pozwala na modyfikacje "
            "i dystrybucję, ale wymaga jasnego oznaczenia zmodyfikowanych wersji. "
            "Wersja 2.0 jest kompatybilna z GPL."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/Artistic-2.0.html",
        aliasy=["Artistic License 2.0", "Artistic-2.0"],
    ),
    # ===== SŁABE COPYLEFT =====
    "LGPL-2.1-only": LicencjaInfo(
        spdx_id="LGPL-2.1-only",
        nazwa="GNU Lesser General Public License v2.1 only",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT,
        opis=(
            "Słaba licencja copyleft przeznaczona dla bibliotek. "
            "Pozwala na dynamiczne linkowanie z oprogramowaniem własnościowym "
            "bez konieczności otwierania kodu projektu. "
            "Modyfikacje samej biblioteki muszą być udostępnione na tej samej licencji. "
            "Kluczowe pytanie: czy biblioteka jest linkowana dynamicznie czy statycznie?"
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/LGPL-2.1-only.html",
        aliasy=[
            "LGPL-2.1",
            "LGPL 2.1",
            "GNU Lesser General Public License v2.1",
            "GNU LGPL",
        ],
    ),
    "LGPL-2.1-or-later": LicencjaInfo(
        spdx_id="LGPL-2.1-or-later",
        nazwa="GNU Lesser General Public License v2.1 or later",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT,
        opis=(
            "Wersja LGPL-2.1 z klauzulą 'lub nowsza'. "
            "Pozwala na stosowanie tej lub nowszej wersji LGPL. "
            "Bardziej elastyczna niż LGPL-2.1-only."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/LGPL-2.1-or-later.html",
        aliasy=["LGPL-2.1+", "LGPL v2.1+"],
    ),
    "LGPL-3.0-only": LicencjaInfo(
        spdx_id="LGPL-3.0-only",
        nazwa="GNU Lesser General Public License v3.0 only",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT,
        opis=(
            "Nowsza wersja LGPL. Podobna do LGPL-2.1, ale oparta na GPL-3.0. "
            "Zawiera klauzulę patentową. Niekompatybilna z GPL-2.0-only. "
            "Wymaga informowania użytkowników o możliwości wymiany biblioteki."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/LGPL-3.0-only.html",
        aliasy=["LGPL-3.0", "LGPL 3.0", "GNU Lesser General Public License v3"],
    ),
    "LGPL-3.0-or-later": LicencjaInfo(
        spdx_id="LGPL-3.0-or-later",
        nazwa="GNU Lesser General Public License v3.0 or later",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT,
        opis="Wersja LGPL-3.0 z klauzulą 'lub nowsza'.",
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/LGPL-3.0-or-later.html",
        aliasy=["LGPL-3.0+", "LGPL v3+"],
    ),
    "MPL-2.0": LicencjaInfo(
        spdx_id="MPL-2.0",
        nazwa="Mozilla Public License 2.0",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT,
        opis=(
            "Licencja na poziomie pliku (file-level copyleft) od Mozilla Foundation. "
            "Zmienione pliki objęte MPL muszą być udostępnione na tej samej licencji, "
            "ale można je łączyć z kodem na innych licencjach (w tym własnościowych) "
            "w oddzielnych plikach. Kompatybilna z GPL-2.0+ i Apache-2.0."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/MPL-2.0.html",
        aliasy=["MPL 2.0", "Mozilla Public License 2.0", "MPLv2.0"],
    ),
    "EUPL-1.2": LicencjaInfo(
        spdx_id="EUPL-1.2",
        nazwa="European Union Public Licence 1.2",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT, # Choć niektórzy uznają ją za SILNE_COPYLEFT z opcją na downgrade
        opis=(
            "Licencja copyleft stworzona przez Unię Europejską. "
            "Interoperacyjna z wieloma innymi licencjami copyleft, w tym GPL. "
            "Przetłumaczona na 23 języki UE — jedyna licencja z takim zasięgiem. "
            "Podobnie jak AGPL, chroni przed luką SaaS (wymaga udostępnienia kodu przy usługach sieciowych). "
            "Używana przez projekty i instytucje publiczne w UE."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/EUPL-1.2.html",
        uzytkowan_sieciowe_wyzwala_copyleft=True,  # POPRAWKA!
        aliasy=["EUPL v1.2", "European Union Public Licence v1.2"],
    ),
    "EPL-2.0": LicencjaInfo(
        spdx_id="EPL-2.0",
        nazwa="Eclipse Public License 2.0",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT,
        opis=(
            "Licencja copyleft od Eclipse Foundation na poziomie modułu. "
            "Kod EPL może być łączony z kodem na innych licencjach. "
            "Modyfikacje kodu EPL muszą być udostępniane. "
            "Zawiera klauzulę patentową. Wersja 2.0 opcjonalnie zezwala "
            "na kompatybilność wtórną (Secondary License) z GNU GPL-2.0+. "
            "Używana przez Eclipse IDE i projekty z nim związane."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/EPL-2.0.html",
        aliasy=["Eclipse Public License 2.0", "EPL 2.0"],
    ),
    "CDDL-1.0": LicencjaInfo(
        spdx_id="CDDL-1.0",
        nazwa="Common Development and Distribution License 1.0",
        poziom_ryzyka=PoziomRyzyka.SLABE_COPYLEFT,
        opis=(
            "Licencja od Sun Microsystems (Oracle) na poziomie pliku. "
            "Podobna do MPL. Zmiany pliku CDDL muszą być udostępnione. "
            "NIEKOMPATYBILNA z GPL według FSF. Używana przez OpenSolaris i GlassFish."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/CDDL-1.0.html",
        aliasy=["CDDL", "Common Development and Distribution License"],
    ),
    # ===== SILNE COPYLEFT =====
    "GPL-2.0-only": LicencjaInfo(
        spdx_id="GPL-2.0-only",
        nazwa="GNU General Public License v2.0 only",
        poziom_ryzyka=PoziomRyzyka.SILNE_COPYLEFT,
        opis=(
            "Silna licencja copyleft — każde oprogramowanie łączące kod GPL-2.0 "
            "musi być udostępnione jako całość na GPL-2.0. "
            "NIEKOMPATYBILNA z Apache-2.0 (ze względu na klauzulę patentową Apache). "
            "NIEKOMPATYBILNA z GPL-3.0-only (różne warunki). "
            "Nie stosuj tej biblioteki w zamkniętym oprogramowaniu."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/GPL-2.0-only.html",
        aliasy=[
            "GPL-2.0",
            "GPL v2",
            "GPL 2.0",
            "GNU GPL v2",
            "GNU General Public License v2",
        ],
    ),
    "GPL-2.0-or-later": LicencjaInfo(
        spdx_id="GPL-2.0-or-later",
        nazwa="GNU General Public License v2.0 or later",
        poziom_ryzyka=PoziomRyzyka.SILNE_COPYLEFT,
        opis=(
            "GPL-2.0 z klauzulą 'lub nowsza'. Projekt może zdecydować się "
            "na stosowanie GPL-3.0. Kompatybilna z Apache-2.0 "
            "(poprzez konwersję do GPL-3.0). Wciąż wymaga udostępnienia kodu."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/GPL-2.0-or-later.html",
        aliasy=["GPL-2.0+", "GPL v2+", "GPL 2.0+"],
    ),
    "GPL-3.0-only": LicencjaInfo(
        spdx_id="GPL-3.0-only",
        nazwa="GNU General Public License v3.0 only",
        poziom_ryzyka=PoziomRyzyka.SILNE_COPYLEFT,
        opis=(
            "Aktualna wersja GPL. Zawiera klauzulę patentową i anty-tivoizacyjną. "
            "Każde oprogramowanie łączące kod GPL-3.0 musi być udostępnione "
            "na GPL-3.0. Kompatybilna z Apache-2.0. "
            "Stosowana przez GNU i wiele ważnych projektów open-source."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/GPL-3.0-only.html",
        aliasy=[
            "GPL-3.0",
            "GPL v3",
            "GPL 3.0",
            "GNU GPL v3",
            "GNU General Public License v3",
            "GPLv3",
        ],
    ),
    "GPL-3.0-or-later": LicencjaInfo(
        spdx_id="GPL-3.0-or-later",
        nazwa="GNU General Public License v3.0 or later",
        poziom_ryzyka=PoziomRyzyka.SILNE_COPYLEFT,
        opis="GPL-3.0 z klauzulą 'lub nowsza'. Identyczne wymogi co GPL-3.0-only.",
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/GPL-3.0-or-later.html",
        aliasy=["GPL-3.0+", "GPL v3+"],
    ),
    "AGPL-3.0-only": LicencjaInfo(
        spdx_id="AGPL-3.0-only",
        nazwa="GNU Affero General Public License v3.0 only",
        poziom_ryzyka=PoziomRyzyka.SILNE_COPYLEFT,
        opis=(
            "Najsilniejsza licencja copyleft. Jak GPL-3.0, ale dodatkowo wymaga "
            "udostępnienia kodu gdy oprogramowanie jest URUCHAMIANE JAKO USŁUGA SIECIOWA "
            "(SaaS, web API). Tzw. 'sieciowe copyleft'. "
            "Twórcy wybrali ją celowo, by zapobiec zamykaniu ich kodu "
            "przez firmy świadczące usługi w chmurze. "
            "Stosowanie w projekcie komercyjnym wymaga osobnej licencji komercyjnej."
        ),
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/AGPL-3.0-only.html",
        uzytkowan_sieciowe_wyzwala_copyleft=True,
        aliasy=[
            "AGPL-3.0",
            "AGPL v3",
            "GNU Affero General Public License v3",
            "AGPLv3",
        ],
    ),
    "AGPL-3.0-or-later": LicencjaInfo(
        spdx_id="AGPL-3.0-or-later",
        nazwa="GNU Affero General Public License v3.0 or later",
        poziom_ryzyka=PoziomRyzyka.SILNE_COPYLEFT,
        opis="AGPL-3.0 z klauzulą 'lub nowsza'. Identyczne wymogi co AGPL-3.0-only.",
        wymaga_udostepnienia_kodu=True,
        zezwala_na_uzytkowan_komercyjne=True,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="https://spdx.org/licenses/AGPL-3.0-or-later.html",
        uzytkowan_sieciowe_wyzwala_copyleft=True,
        aliasy=["AGPL-3.0+", "AGPL v3+"],
    ),
    # ===== WŁASNOŚCIOWE =====
    "Proprietary": LicencjaInfo(
        spdx_id="Proprietary",
        nazwa="Proprietary / Commercial License",
        poziom_ryzyka=PoziomRyzyka.WLASNOSCI,
        opis=(
            "Licencja własnościowa lub komercyjna. Warunki użytkowania "
            "zdefiniowane są przez właściciela praw autorskich. "
            "Zazwyczaj zabrania redystrybucji i modyfikacji. "
            "Wymaga indywidualnej analizy i ewentualnego zakupu licencji."
        ),
        wymaga_udostepnienia_kodu=False,
        zezwala_na_uzytkowan_komercyjne=False,
        wymaga_zachowania_informacji_autorskich=True,
        link_spdx="",
        aliasy=["Proprietary", "Commercial", "proprietary"],
    ),
}

# ---------------------------------------------------------------------------
# Słownik aliasów → SPDX ID (zbudowany automatycznie z bazy)
# ---------------------------------------------------------------------------
_ALIAS_DO_SPDX: dict[str, str] = {}

for _spdx_id, _info in ZNANE_LICENCJE.items():
    _ALIAS_DO_SPDX[_spdx_id.lower()] = _spdx_id
    for _alias in _info.aliasy:
        _ALIAS_DO_SPDX[_alias.lower()] = _spdx_id

# Dodatkowe ręczne mapowania często spotykanych wariantów
_DODATKOWE_ALIASY: dict[str, str] = {
    "gpl2": "GPL-2.0-only",
    "gpl3": "GPL-3.0-only",
    "gpl": "GPL-3.0-only",
    "lgpl": "LGPL-3.0-only",
    "agpl": "AGPL-3.0-only",
    "mpl": "MPL-2.0",
    "apache": "Apache-2.0",
    "apache license": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "bsd-like": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "modified bsd license": "BSD-3-Clause",
    "isc": "ISC",
    "isc license (iscl)": "ISC",
    "python-2.0": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    "psfl": "PSF-2.0",
    "python license (psfl)": "PSF-2.0",
    "0bsd": "BSD-2-Clause",
    "cc-0": "CC0-1.0",
    "cc0": "CC0-1.0",
    "public domain": "Unlicense",
    "wtfpl": "Unlicense",
    "gnu lgpl": "LGPL-3.0-only",
    "lgplv2": "LGPL-2.1-only",
    "lgplv3": "LGPL-3.0-only",
    "gplv2": "GPL-2.0-only",
    "gplv3": "GPL-3.0-only",
    "agplv3": "AGPL-3.0-only",
    "eclipse public license": "EPL-2.0",
    "mozilla public license": "MPL-2.0",
    "european union public licence": "EUPL-1.2",
    # Warianty z klasyfikatorów PyPI ("License :: OSI Approved :: X")
    "osi approved :: mit license": "MIT",
    "osi approved :: apache software license": "Apache-2.0",
    "osi approved :: bsd license": "BSD-3-Clause",
    "osi approved :: gnu general public license v3 (gplv3)": "GPL-3.0-only",
    "osi approved :: gnu general public license v2 (gplv2)": "GPL-2.0-only",
    "osi approved :: gnu lesser general public license v3 (lgplv3)": "LGPL-3.0-only",
    "osi approved :: mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "osi approved :: isc license (iscl)": "ISC",
    "osi approved :: python software foundation license": "PSF-2.0",
    "osi approved :: boost software license 1.0 (bsl-1.0)": "BSL-1.0",
    "osi approved :: european union public licence 1.2 (eupl 1.2)": "EUPL-1.2",
    # PEP 639 / SPDX expression (proste przypadki)
    "lgpl with exceptions": "LGPL-2.1-only",
    "lgpl with linking exception": "LGPL-2.1-only",
    "gnu library or lesser general public license (lgpl)": "LGPL-2.1-only",
    "gnu lesser general public license": "LGPL-3.0-only",
    "mit or apache-2.0": "MIT",  # Uproszczenie — weź pierwszą
}
_ALIAS_DO_SPDX.update(_DODATKOWE_ALIASY)


# ---------------------------------------------------------------------------
# Macierz niekompatybilności licencji
# ---------------------------------------------------------------------------
# Każda para (a, b) oznacza, że licencja A i B są niekompatybilne.
# Powody oparte na: https://www.gnu.org/licenses/license-compatibility.html
NIEKOMPATYBILNE_PARY: list[tuple[str, str, str]] = [
    (
        "GPL-2.0-only",
        "Apache-2.0",
        "GPL-2.0-only jest niekompatybilne z Apache-2.0 ze względu na klauzulę patentową "
        "Apache, która nakłada dodatkowe ograniczenia względem GPL-2.0. "
        "(Źródło: FSF — https://www.gnu.org/licenses/license-list.html)",
    ),
    (
        "GPL-2.0-only",
        "GPL-3.0-only",
        "GPL-2.0-only i GPL-3.0-only mają niekompatybilne warunki — "
        "kod 'GPL-2.0 only' nie może być dystrybuowany na GPL-3.0.",
    ),
    (
        "GPL-2.0-only",
        "AGPL-3.0-only",
        "GPL-2.0-only jest niekompatybilne z AGPL-3.0-only.",
    ),
    (
        "GPL-2.0-only",
        "AGPL-3.0-or-later",
        "GPL-2.0-only jest niekompatybilne z AGPL-3.0.",
    ),
    (
        "GPL-2.0-only",
        "GPL-3.0-or-later",
        "Kod 'GPL-2.0 only' nie może być objęty licencją GPL-3.0.",
    ),
    (
        "GPL-2.0-only",
        "EUPL-1.2",
        "EUPL-1.2 jest niekompatybilne z GPL-2.0-only.",
    ),
    (
        "CDDL-1.0",
        "GPL-2.0-only",
        "CDDL-1.0 jest niekompatybilne z GPL-2.0-only według FSF.",
    ),
    (
        "CDDL-1.0",
        "GPL-3.0-only",
        "CDDL-1.0 jest niekompatybilne z GPL-3.0-only według FSF.",
    ),
    (
        "CDDL-1.0",
        "GPL-2.0-or-later",
        "CDDL-1.0 jest niekompatybilne z GPL.",
    ),
    (
        "CDDL-1.0",
        "GPL-3.0-or-later",
        "CDDL-1.0 jest niekompatybilne z GPL.",
    ),
]


def normalizuj_nazwe_licencji(nazwa: str | None) -> str | None:
    """
    Normalizuje nazwę licencji do identyfikatora SPDX.

    Args:
        nazwa: Surowa nazwa licencji (np. "MIT License", "Apache 2.0").

    Returns:
        Identyfikator SPDX lub None jeśli nie można znormalizować.
    """
    if not nazwa:
        return None
    nazwa_clean = nazwa.strip()
    # Próba bezpośredniego dopasowania (ignorując wielkość liter)
    wynik = _ALIAS_DO_SPDX.get(nazwa_clean.lower())
    if wynik:
        return wynik
    # Próba częściowego dopasowania dla typowych wzorców
    # Sortowanie od najdłuższego aliasu — zapobiega dopasowaniu krótszego
    # podciągu przed dłuższym (np. 'gpl' nie wyprzedza 'lgpl').
    nazwa_lower = nazwa_clean.lower()
    for alias, spdx_id in sorted(_ALIAS_DO_SPDX.items(), key=lambda x: -len(x[0])):
        if alias in nazwa_lower or nazwa_lower in alias:
            return spdx_id
    return None


def pobierz_info_licencji(spdx_id: str | None) -> LicencjaInfo | None:
    """
    Pobiera informacje o licencji na podstawie jej SPDX ID.

    Args:
        spdx_id: Identyfikator SPDX licencji.

    Returns:
        LicencjaInfo lub None jeśli licencja nie jest w bazie.
    """
    if not spdx_id:
        return None
    return ZNANE_LICENCJE.get(spdx_id)


def sprawdz_niekompatybilnosc(
    licencja_a: str, licencja_b: str
) -> str | None:
    """
    Sprawdza czy dwie licencje są niekompatybilne.

    Args:
        licencja_a: SPDX ID pierwszej licencji.
        licencja_b: SPDX ID drugiej licencji.

    Returns:
        Opis konfliktu lub None jeśli licencje są kompatybilne.
    """
    for a, b, powod in NIEKOMPATYBILNE_PARY:
        if (licencja_a == a and licencja_b == b) or (
            licencja_a == b and licencja_b == a
        ):
            return powod
    return None
