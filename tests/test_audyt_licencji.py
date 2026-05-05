"""
Testy jednostkowe dla modułów audytu licencji.

Testują:
- Normalizację nazw licencji (licencje.py)
- Skanowanie plików manifestowych (skaner.py)
- Walidację nazw pakietów (pobieracz.py)
- Klasyfikację ryzyka i wykrywanie konfliktów (analizator.py)

Testy nie wymagają połączenia z internetem — używają danych mockowanych.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Dodaj src do ścieżki Pythona
_PROJEKT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJEKT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


# ---------------------------------------------------------------------------
# Testy normalizacji licencji (licencje.py)
# ---------------------------------------------------------------------------


class TestNormalizacjaLicencji(unittest.TestCase):
    """Testy normalizacji nazw licencji do SPDX ID."""

    def test_mit_rozne_warianty(self):
        from licencje import normalizuj_nazwe_licencji

        for nazwa in ["MIT", "mit", "MIT License", "The MIT License", "Expat License"]:
            with self.subTest(nazwa=nazwa):
                wynik = normalizuj_nazwe_licencji(nazwa)
                self.assertEqual(wynik, "MIT", f"Oczekiwano MIT dla '{nazwa}'")

    def test_apache_rozne_warianty(self):
        from licencje import normalizuj_nazwe_licencji

        for nazwa in ["Apache-2.0", "Apache License 2.0", "Apache 2.0", "Apache2"]:
            with self.subTest(nazwa=nazwa):
                wynik = normalizuj_nazwe_licencji(nazwa)
                self.assertEqual(wynik, "Apache-2.0", f"Oczekiwano Apache-2.0 dla '{nazwa}'")

    def test_gpl_warianty(self):
        from licencje import normalizuj_nazwe_licencji

        mapowanie = {
            "GPL-3.0": "GPL-3.0-only",
            "GPL v3": "GPL-3.0-only",
            "GPLv3": "GPL-3.0-only",
            "GPL-2.0": "GPL-2.0-only",
            "GPL v2": "GPL-2.0-only",
        }
        for nazwa, oczekiwane in mapowanie.items():
            with self.subTest(nazwa=nazwa):
                wynik = normalizuj_nazwe_licencji(nazwa)
                self.assertEqual(wynik, oczekiwane, f"Oczekiwano {oczekiwane} dla '{nazwa}'")

    def test_none_zwraca_none(self):
        from licencje import normalizuj_nazwe_licencji

        self.assertIsNone(normalizuj_nazwe_licencji(None))

    def test_pusty_string_zwraca_none(self):
        from licencje import normalizuj_nazwe_licencji

        self.assertIsNone(normalizuj_nazwe_licencji(""))

    def test_nieznana_licencja_zwraca_none(self):
        from licencje import normalizuj_nazwe_licencji

        wynik = normalizuj_nazwe_licencji("Bardzo Egzotyczna Licencja XYZ-999")
        self.assertIsNone(wynik)

    def test_bsd_warianty(self):
        from licencje import normalizuj_nazwe_licencji

        self.assertEqual(normalizuj_nazwe_licencji("BSD-3-Clause"), "BSD-3-Clause")
        self.assertEqual(normalizuj_nazwe_licencji("New BSD"), "BSD-3-Clause")

    def test_poziom_ryzyka_bezpieczna(self):
        from licencje import pobierz_info_licencji, PoziomRyzyka

        for spdx in ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "Unlicense"]:
            info = pobierz_info_licencji(spdx)
            self.assertIsNotNone(info, f"Brak info dla {spdx}")
            self.assertEqual(
                info.poziom_ryzyka,
                PoziomRyzyka.BEZPIECZNA,
                f"{spdx} powinno być bezpieczne",
            )

    def test_poziom_ryzyka_silne_copyleft(self):
        from licencje import pobierz_info_licencji, PoziomRyzyka

        for spdx in ["GPL-2.0-only", "GPL-3.0-only", "AGPL-3.0-only"]:
            info = pobierz_info_licencji(spdx)
            self.assertIsNotNone(info, f"Brak info dla {spdx}")
            self.assertEqual(
                info.poziom_ryzyka,
                PoziomRyzyka.SILNE_COPYLEFT,
                f"{spdx} powinno być silne copyleft",
            )

    def test_gpl2_apache_niekompatybilne(self):
        from licencje import sprawdz_niekompatybilnosc

        wynik = sprawdz_niekompatybilnosc("GPL-2.0-only", "Apache-2.0")
        self.assertIsNotNone(wynik, "GPL-2.0-only i Apache-2.0 powinny być niekompatybilne")

    def test_mit_apache_kompatybilne(self):
        from licencje import sprawdz_niekompatybilnosc

        wynik = sprawdz_niekompatybilnosc("MIT", "Apache-2.0")
        self.assertIsNone(wynik, "MIT i Apache-2.0 powinny być kompatybilne")


# ---------------------------------------------------------------------------
# Testy skanowania plików (skaner.py)
# ---------------------------------------------------------------------------


class TestSkaner(unittest.TestCase):
    """Testy skanowania plików manifestowych."""

    def _stworz_katalog_temp(self) -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory()

    def test_skanuj_requirements_txt(self):
        from skaner import _skanuj_requirements_txt

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(
                "requests==2.31.0\n"
                "numpy>=1.24.0\n"
                "# komentarz\n"
                "\n"
                "pandas~=2.0\n"
                "flask[async]>=3.0\n"
            )
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_requirements_txt(sciezka)
            nazwy = [d.nazwa for d in wynik]
            self.assertIn("requests", nazwy)
            self.assertIn("numpy", nazwy)
            self.assertIn("pandas", nazwy)
            self.assertIn("flask", nazwy)
            # Sprawdź wersję dokładną
            requests_dep = next(d for d in wynik if d.nazwa == "requests")
            self.assertEqual(requests_dep.wersja, "2.31.0")
            # Sprawdź ekosystem
            self.assertTrue(all(d.ekosystem == "pypi" for d in wynik))
        finally:
            sciezka.unlink(missing_ok=True)

    def test_skanuj_requirements_ignoruje_komentarze(self):
        from skaner import _skanuj_requirements_txt

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("# To jest komentarz\n# requests==1.0\n\n-r other.txt\n")
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_requirements_txt(sciezka)
            self.assertEqual(len(wynik), 0, "Powinno być 0 zależności (same komentarze)")
        finally:
            sciezka.unlink(missing_ok=True)

    def test_skanuj_pyproject_toml_pep621(self):
        from skaner import _skanuj_pyproject_toml

        tresc = """
[project]
name = "test-projekt"
version = "1.0.0"
dependencies = [
    "requests>=2.0",
    "click==8.1.0",
    "numpy",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "black>=23.0"]
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False, encoding="utf-8"
        ) as f:
            f.write(tresc)
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_pyproject_toml(sciezka)
            nazwy = {d.nazwa for d in wynik}
            self.assertIn("requests", nazwy)
            self.assertIn("click", nazwy)
            self.assertIn("numpy", nazwy)
            self.assertIn("pytest", nazwy)
            self.assertIn("black", nazwy)
            # Sprawdź wersję
            click_dep = next(d for d in wynik if d.nazwa == "click")
            self.assertEqual(click_dep.wersja, "8.1.0")
        finally:
            sciezka.unlink(missing_ok=True)

    def test_skanuj_package_json(self):
        from skaner import _skanuj_package_json

        dane = {
            "name": "test-projekt",
            "dependencies": {
                "express": "^4.18.0",
                "axios": "^1.6.0",
            },
            "devDependencies": {
                "jest": "^29.0.0",
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(dane, f)
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_package_json(sciezka)
            nazwy = {d.nazwa for d in wynik}
            self.assertIn("express", nazwy)
            self.assertIn("axios", nazwy)
            self.assertIn("jest", nazwy)
            self.assertTrue(all(d.ekosystem == "npm" for d in wynik))
        finally:
            sciezka.unlink(missing_ok=True)

    def test_deduplikacja(self):
        from skaner import _deduplikuj, Zaleznosc

        zaleznie = [
            Zaleznosc("requests", "2.31.0", "pypi", "req.txt"),
            Zaleznosc("Requests", "2.32.0", "pypi", "pyproject.toml"),  # duplikat
            Zaleznosc("numpy", None, "pypi", "req.txt"),
        ]
        wynik = _deduplikuj(zaleznie)
        self.assertEqual(len(wynik), 2)
        nazwy = [d.nazwa for d in wynik]
        self.assertIn("requests", nazwy)
        self.assertIn("numpy", nazwy)

    def test_pomijanie_node_modules(self):
        from skaner import _pominij_sciezke

        self.assertTrue(_pominij_sciezke(Path("node_modules/express/package.json")))
        self.assertTrue(_pominij_sciezke(Path(".venv/lib/requests/setup.cfg")))
        self.assertFalse(_pominij_sciezke(Path("src/requirements.txt")))
        self.assertFalse(_pominij_sciezke(Path("pyproject.toml")))


# ---------------------------------------------------------------------------
# Testy walidacji nazw pakietów (pobieracz.py)
# ---------------------------------------------------------------------------


class TestWalidacjaNazw(unittest.TestCase):
    """Testy walidacji nazw pakietów — ochrona przed path traversal."""

    def test_poprawna_nazwa_pypi(self):
        from pobieracz import _waliduj_nazwe_pakietu

        for nazwa in ["requests", "numpy", "scikit-learn", "my_package.v2", "Package123"]:
            with self.subTest(nazwa=nazwa):
                self.assertTrue(_waliduj_nazwe_pakietu(nazwa))

    def test_niebezpieczna_nazwa_pypi(self):
        from pobieracz import _waliduj_nazwe_pakietu

        for nazwa in ["../evil", "pkg;rm -rf /", "", "a" * 201, "pkg name"]:
            with self.subTest(nazwa=nazwa):
                self.assertFalse(_waliduj_nazwe_pakietu(nazwa))

    def test_poprawna_nazwa_npm_scoped(self):
        from pobieracz import _waliduj_nazwe_pakietu_npm

        self.assertTrue(_waliduj_nazwe_pakietu_npm("@types/node"))
        self.assertTrue(_waliduj_nazwe_pakietu_npm("@scope/package-name"))
        self.assertTrue(_waliduj_nazwe_pakietu_npm("express"))

    def test_niebezpieczna_nazwa_npm(self):
        from pobieracz import _waliduj_nazwe_pakietu_npm

        self.assertFalse(_waliduj_nazwe_pakietu_npm(""))
        self.assertFalse(_waliduj_nazwe_pakietu_npm("../etc/passwd"))


# ---------------------------------------------------------------------------
# Testy analizatora (analizator.py)
# ---------------------------------------------------------------------------


class TestAnalizator(unittest.TestCase):
    """Testy analizy licencji i wykrywania konfliktów."""

    def _stworz_zaleznosc(self, nazwa, licencja_surowa, ekosystem="pypi"):
        from skaner import Zaleznosc
        from pobieracz import WynikPobierania

        dep = Zaleznosc(nazwa=nazwa, wersja="1.0.0", ekosystem=ekosystem, plik_zrodlowy="req.txt")
        wynik = WynikPobierania(
            nazwa=nazwa,
            wersja="1.0.0",
            ekosystem=ekosystem,
            licencja_surowa=licencja_surowa,
            url_zrodla=f"https://pypi.org/project/{nazwa}/",
        )
        return dep, wynik

    def test_klasyfikacja_mit(self):
        from analizator import analizuj_zaleznie
        from licencje import PoziomRyzyka

        dep, wynik = self._stworz_zaleznosc("requests", "MIT")
        wynik_analizy = analizuj_zaleznie([dep], [wynik])
        analiza = wynik_analizy.zaleznie_analizy[0]
        self.assertEqual(analiza.poziom_ryzyka, PoziomRyzyka.BEZPIECZNA)

    def test_klasyfikacja_gpl(self):
        from analizator import analizuj_zaleznie
        from licencje import PoziomRyzyka

        dep, wynik = self._stworz_zaleznosc("some-gpl-lib", "GPL-3.0")
        wynik_analizy = analizuj_zaleznie([dep], [wynik])
        analiza = wynik_analizy.zaleznie_analizy[0]
        self.assertEqual(analiza.poziom_ryzyka, PoziomRyzyka.SILNE_COPYLEFT)

    def test_klasyfikacja_agpl(self):
        from analizator import analizuj_zaleznie
        from licencje import PoziomRyzyka

        dep, wynik = self._stworz_zaleznosc("agpl-lib", "AGPL v3")
        wynik_analizy = analizuj_zaleznie([dep], [wynik])
        analiza = wynik_analizy.zaleznie_analizy[0]
        self.assertEqual(analiza.poziom_ryzyka, PoziomRyzyka.SILNE_COPYLEFT)

    def test_klasyfikacja_nieznana(self):
        from analizator import analizuj_zaleznie
        from licencje import PoziomRyzyka

        dep, wynik = self._stworz_zaleznosc("tajemniczy-pakiet", None)
        wynik_analizy = analizuj_zaleznie([dep], [wynik])
        analiza = wynik_analizy.zaleznie_analizy[0]
        self.assertEqual(analiza.poziom_ryzyka, PoziomRyzyka.NIEZNANA)

    def test_wykrywanie_konfliktu_gpl2_apache(self):
        from analizator import analizuj_zaleznie

        dep_a, wynik_a = self._stworz_zaleznosc("lib-gpl2", "GPL-2.0")
        dep_b, wynik_b = self._stworz_zaleznosc("lib-apache", "Apache-2.0")
        wynik_analizy = analizuj_zaleznie([dep_a, dep_b], [wynik_a, wynik_b])
        self.assertGreater(
            len(wynik_analizy.konflikty), 0,
            "Powinien być wykryty konflikt GPL-2.0 ↔ Apache-2.0"
        )

    def test_brak_konfliktu_mit_apache(self):
        from analizator import analizuj_zaleznie

        dep_a, wynik_a = self._stworz_zaleznosc("lib-mit", "MIT")
        dep_b, wynik_b = self._stworz_zaleznosc("lib-apache", "Apache-2.0")
        wynik_analizy = analizuj_zaleznie([dep_a, dep_b], [wynik_a, wynik_b])
        self.assertEqual(
            len(wynik_analizy.konflikty), 0,
            "MIT i Apache-2.0 nie powinny tworzyć konfliktu"
        )

    def test_statystyki_ryzyka(self):
        from analizator import analizuj_zaleznie
        from licencje import PoziomRyzyka

        deps_wyniki = [
            self._stworz_zaleznosc("a", "MIT"),
            self._stworz_zaleznosc("b", "Apache-2.0"),
            self._stworz_zaleznosc("c", "GPL-3.0"),
            self._stworz_zaleznosc("d", None),
        ]
        zaleznie = [d for d, _ in deps_wyniki]
        wyniki = [w for _, w in deps_wyniki]

        wynik_analizy = analizuj_zaleznie(zaleznie, wyniki)
        stats = wynik_analizy.statystyki_ryzyka

        self.assertEqual(stats[PoziomRyzyka.BEZPIECZNA], 2)
        self.assertEqual(stats[PoziomRyzyka.SILNE_COPYLEFT], 1)
        self.assertEqual(stats[PoziomRyzyka.NIEZNANA], 1)
        self.assertEqual(wynik_analizy.liczba_zaleznie, 4)
        self.assertTrue(wynik_analizy.ma_wysokie_ryzyko)

    def test_generuj_rekomendacje_agpl(self):
        from analizator import analizuj_zaleznie, generuj_rekomendacje

        dep, wynik = self._stworz_zaleznosc("lib-agpl", "AGPL-3.0")
        wynik_analizy = analizuj_zaleznie([dep], [wynik])
        rekomendacje = generuj_rekomendacje(wynik_analizy)
        # Rekomendacja powinna wspominać o AGPL
        tekst = " ".join(rekomendacje)
        self.assertIn("AGPL", tekst)

    def test_generuj_rekomendacje_ok(self):
        from analizator import analizuj_zaleznie, generuj_rekomendacje

        dep, wynik = self._stworz_zaleznosc("lib-mit", "MIT")
        wynik_analizy = analizuj_zaleznie([dep], [wynik])
        rekomendacje = generuj_rekomendacje(wynik_analizy)
        tekst = " ".join(rekomendacje)
        self.assertIn("Brak krytycznych problemów", tekst)


# ---------------------------------------------------------------------------
# Testy raportu (raport.py) — tylko tekst (HTML wymaga Jinja2)
# ---------------------------------------------------------------------------


class TestRaportTekstowy(unittest.TestCase):
    """Testy generowania raportu tekstowego."""

    def _stworz_prosty_wynik(self):
        from analizator import analizuj_zaleznie
        from skaner import Zaleznosc
        from pobieracz import WynikPobierania

        zaleznie = [
            Zaleznosc("requests", "2.31.0", "pypi", "req.txt"),
            Zaleznosc("gpl-lib", "1.0.0", "pypi", "req.txt"),
        ]
        wyniki = [
            WynikPobierania("requests", "2.31.0", "pypi", "MIT", "https://pypi.org/project/requests/"),
            WynikPobierania("gpl-lib", "1.0.0", "pypi", "GPL-3.0", "https://pypi.org/project/gpl-lib/"),
        ]
        return analizuj_zaleznie(zaleznie, wyniki)

    def test_raport_tekstowy_zawiera_nazwy(self):
        from raport import drukuj_raport_tekstowy

        wynik = self._stworz_prosty_wynik()
        tekst = drukuj_raport_tekstowy(wynik, "Test Projekt")

        self.assertIn("requests", tekst)
        self.assertIn("gpl-lib", tekst)
        self.assertIn("Test Projekt".upper(), tekst)

    def test_raport_json_struktura(self):
        from raport import generuj_raport_json
        import json

        wynik = self._stworz_prosty_wynik()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            sciezka = Path(f.name)

        try:
            generuj_raport_json(wynik, sciezka, "Test Projekt")
            dane = json.loads(sciezka.read_text(encoding="utf-8"))
            self.assertIn("projekt", dane)
            self.assertIn("podsumowanie", dane)
            self.assertIn("zaleznosci", dane)
            self.assertIn("konflikty", dane)
            self.assertIn("rekomendacje", dane)
            self.assertEqual(dane["projekt"], "Test Projekt")
            self.assertEqual(dane["podsumowanie"]["liczba_zaleznosci"], 2)
        finally:
            sciezka.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Testy skanera — setup.cfg i Pipfile
# ---------------------------------------------------------------------------


class TestSkanerDodatkowe(unittest.TestCase):
    """Testy skanowania formatów setup.cfg i Pipfile."""

    def test_skanuj_setup_cfg(self):
        from skaner import _skanuj_setup_cfg

        tresc = """
[metadata]
name = test-projekt

[options]
install_requires =
    requests>=2.0
    click==8.1.0
    numpy

[options.extras_require]
dev =
    pytest>=7.0
    black
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".cfg", delete=False, encoding="utf-8"
        ) as f:
            f.write(tresc)
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_setup_cfg(sciezka)
            nazwy = {d.nazwa for d in wynik}
            self.assertIn("requests", nazwy)
            self.assertIn("click", nazwy)
            self.assertIn("numpy", nazwy)
            self.assertIn("pytest", nazwy)
            self.assertIn("black", nazwy)
            self.assertTrue(all(d.ekosystem == "pypi" for d in wynik))
        finally:
            sciezka.unlink(missing_ok=True)

    def test_skanuj_setup_cfg_pusty(self):
        from skaner import _skanuj_setup_cfg

        tresc = "[metadata]\nname = test\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".cfg", delete=False, encoding="utf-8"
        ) as f:
            f.write(tresc)
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_setup_cfg(sciezka)
            self.assertEqual(len(wynik), 0)
        finally:
            sciezka.unlink(missing_ok=True)

    def test_skanuj_pipfile(self):
        from skaner import _skanuj_pipfile

        tresc = """
[packages]
requests = "*"
click = "==8.1.0"

[dev-packages]
pytest = ">=7.0"
black = "*"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="", prefix="Pipfile_", delete=False, encoding="utf-8"
        ) as f:
            f.write(tresc)
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_pipfile(sciezka)
            nazwy = {d.nazwa for d in wynik}
            self.assertIn("requests", nazwy)
            self.assertIn("click", nazwy)
            self.assertIn("pytest", nazwy)
            self.assertIn("black", nazwy)
            # Sprawdź wersję dokładną
            click_dep = next(d for d in wynik if d.nazwa == "click")
            self.assertEqual(click_dep.wersja, "8.1.0")
            self.assertTrue(all(d.ekosystem == "pypi" for d in wynik))
        finally:
            sciezka.unlink(missing_ok=True)

    def test_skanuj_pipfile_ignoruje_python(self):
        from skaner import _skanuj_pipfile

        tresc = """
[packages]
requests = "*"
python_requires = ">=3.9"

[requires]
python_version = "3.11"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="", prefix="Pipfile_", delete=False, encoding="utf-8"
        ) as f:
            f.write(tresc)
            sciezka = Path(f.name)

        try:
            wynik = _skanuj_pipfile(sciezka)
            nazwy = {d.nazwa.lower() for d in wynik}
            self.assertNotIn("python", nazwy)
        finally:
            sciezka.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Testy analizatora — parsowanie klasyfikatorów PyPI i właściwości WynikAnalizy
# ---------------------------------------------------------------------------


class TestAnalizatorDodatkowe(unittest.TestCase):
    """Testy parsowania klasyfikatorów PyPI i właściwości WynikAnalizy."""

    def test_parsuj_klasyfikator_pypi_mit(self):
        from analizator import _parsuj_klasyfikator_pypi

        wynik = _parsuj_klasyfikator_pypi(
            "License :: OSI Approved :: MIT License"
        )
        self.assertEqual(wynik, "MIT")

    def test_parsuj_klasyfikator_pypi_apache(self):
        from analizator import _parsuj_klasyfikator_pypi

        wynik = _parsuj_klasyfikator_pypi(
            "License :: OSI Approved :: Apache Software License"
        )
        self.assertEqual(wynik, "Apache-2.0")

    def test_parsuj_klasyfikator_pypi_brak_separatora(self):
        from analizator import _parsuj_klasyfikator_pypi

        # Brak "::" — nie jest klasyfikatorem PyPI
        wynik = _parsuj_klasyfikator_pypi("MIT License")
        self.assertIsNone(wynik)

    def test_parsuj_klasyfikator_pypi_nie_licencja(self):
        from analizator import _parsuj_klasyfikator_pypi

        wynik = _parsuj_klasyfikator_pypi(
            "Programming Language :: Python :: 3"
        )
        self.assertIsNone(wynik)

    def _stworz_wynik_analizy(self):
        """Tworzy przykładowy WynikAnalizy z 4 zależnościami."""
        from analizator import analizuj_zaleznie
        from skaner import Zaleznosc
        from pobieracz import WynikPobierania

        zaleznie = [
            Zaleznosc("mit-lib", "1.0", "pypi", "req.txt"),
            Zaleznosc("apache-lib", "1.0", "pypi", "req.txt"),
            Zaleznosc("gpl-lib", "1.0", "pypi", "req.txt"),
            Zaleznosc("nieznana-lib", "1.0", "pypi", "req.txt"),
        ]
        wyniki = [
            WynikPobierania("mit-lib", "1.0", "pypi", "MIT", "https://pypi.org/"),
            WynikPobierania("apache-lib", "1.0", "pypi", "Apache-2.0", "https://pypi.org/"),
            WynikPobierania("gpl-lib", "1.0", "pypi", "GPL-3.0", "https://pypi.org/"),
            WynikPobierania("nieznana-lib", "1.0", "pypi", None, "https://pypi.org/"),
        ]
        return analizuj_zaleznie(zaleznie, wyniki)

    def test_wynik_analizy_filtruj_po_ryzyku(self):
        from licencje import PoziomRyzyka

        wynik = self._stworz_wynik_analizy()
        bezpieczne = wynik.filtruj_po_ryzyku(PoziomRyzyka.BEZPIECZNA)
        self.assertEqual(len(bezpieczne), 2)
        nazwy = {z.zaleznosc.nazwa for z in bezpieczne}
        self.assertIn("mit-lib", nazwy)
        self.assertIn("apache-lib", nazwy)

    def test_wynik_analizy_procenty_ryzyka(self):
        from licencje import PoziomRyzyka

        wynik = self._stworz_wynik_analizy()
        procenty = wynik.procenty_ryzyka
        self.assertAlmostEqual(procenty[PoziomRyzyka.BEZPIECZNA], 50.0)
        self.assertAlmostEqual(procenty[PoziomRyzyka.SILNE_COPYLEFT], 25.0)
        self.assertAlmostEqual(procenty[PoziomRyzyka.NIEZNANA], 25.0)

    def test_wynik_analizy_ma_nieznane_licencje(self):
        wynik = self._stworz_wynik_analizy()
        self.assertTrue(wynik.ma_nieznane_licencje)

    def test_wynik_analizy_bez_nieznanych(self):
        from analizator import analizuj_zaleznie
        from skaner import Zaleznosc
        from pobieracz import WynikPobierania

        zaleznie = [Zaleznosc("lib", "1.0", "pypi", "req.txt")]
        wyniki = [WynikPobierania("lib", "1.0", "pypi", "MIT", "https://pypi.org/")]
        wynik = analizuj_zaleznie(zaleznie, wyniki)
        self.assertFalse(wynik.ma_nieznane_licencje)

    def test_analizuj_zaleznie_niezgodna_dlugosc(self):
        from analizator import analizuj_zaleznie
        from skaner import Zaleznosc
        from pobieracz import WynikPobierania

        zaleznie = [Zaleznosc("lib", "1.0", "pypi", "req.txt")]
        wyniki = []
        with self.assertRaises(ValueError):
            analizuj_zaleznie(zaleznie, wyniki)

    def test_wynik_analizy_pusta_lista(self):
        from analizator import analizuj_zaleznie

        wynik = analizuj_zaleznie([], [])
        self.assertEqual(wynik.liczba_zaleznie, 0)
        self.assertEqual(len(wynik.konflikty), 0)
        self.assertFalse(wynik.ma_wysokie_ryzyko)
        self.assertFalse(wynik.ma_nieznane_licencje)


# ---------------------------------------------------------------------------
# Testy pobieracza — _wyciagnij_licencje_pypi / _wyciagnij_licencje_npm
# ---------------------------------------------------------------------------


class TestPobieraczWyciaganie(unittest.TestCase):
    """Testy parsowania odpowiedzi API PyPI i npm."""

    # --- PyPI ---

    def test_wyciagnij_pypi_license_expression(self):
        from pobieracz import _wyciagnij_licencje_pypi

        info = {"license_expression": "MIT", "license": None, "classifiers": []}
        self.assertEqual(_wyciagnij_licencje_pypi(info), "MIT")

    def test_wyciagnij_pypi_license_expression_zlozone(self):
        from pobieracz import _wyciagnij_licencje_pypi

        # Złożone wyrażenie SPDX — weź pierwszą część przed spację
        info = {"license_expression": "MIT AND Apache-2.0", "license": None, "classifiers": []}
        wynik = _wyciagnij_licencje_pypi(info)
        self.assertEqual(wynik, "MIT")

    def test_wyciagnij_pypi_pole_license(self):
        from pobieracz import _wyciagnij_licencje_pypi

        info = {"license_expression": None, "license": "MIT", "classifiers": []}
        self.assertEqual(_wyciagnij_licencje_pypi(info), "MIT")

    def test_wyciagnij_pypi_klasyfikator_fallback(self):
        from pobieracz import _wyciagnij_licencje_pypi

        info = {
            "license_expression": None,
            "license": None,
            "classifiers": [
                "Programming Language :: Python :: 3",
                "License :: OSI Approved :: Apache Software License",
            ],
        }
        wynik = _wyciagnij_licencje_pypi(info)
        self.assertEqual(wynik, "Apache Software License")

    def test_wyciagnij_pypi_unknown_zwraca_none(self):
        from pobieracz import _wyciagnij_licencje_pypi

        info = {"license_expression": "UNKNOWN", "license": "UNKNOWN", "classifiers": []}
        self.assertIsNone(_wyciagnij_licencje_pypi(info))

    def test_wyciagnij_pypi_pusty_zwraca_none(self):
        from pobieracz import _wyciagnij_licencje_pypi

        self.assertIsNone(_wyciagnij_licencje_pypi({}))

    # --- npm ---

    def test_wyciagnij_npm_string(self):
        from pobieracz import _wyciagnij_licencje_npm

        self.assertEqual(_wyciagnij_licencje_npm({"license": "MIT"}), "MIT")

    def test_wyciagnij_npm_slownik(self):
        from pobieracz import _wyciagnij_licencje_npm

        # Stary format npm: {"license": {"type": "MIT", "url": "..."}}
        self.assertEqual(
            _wyciagnij_licencje_npm({"license": {"type": "ISC", "url": "https://..."}}),
            "ISC",
        )

    def test_wyciagnij_npm_tablica(self):
        from pobieracz import _wyciagnij_licencje_npm

        # Jeszcze starszy format: {"licenses": [{"type": "BSD"}]}
        self.assertEqual(
            _wyciagnij_licencje_npm({"licenses": [{"type": "BSD-2-Clause"}]}),
            "BSD-2-Clause",
        )

    def test_wyciagnij_npm_brak_licencji(self):
        from pobieracz import _wyciagnij_licencje_npm

        self.assertIsNone(_wyciagnij_licencje_npm({}))

    # --- pobierz_licencje dispatch ---

    def test_pobierz_licencje_nieznany_ekosystem(self):
        from pobieracz import pobierz_licencje

        wynik = pobierz_licencje("jakis-pakiet", "cargo")
        self.assertIsNotNone(wynik.blad)
        self.assertIn("cargo", wynik.blad.lower())

    def test_pobierz_licencje_nieprawidlowa_nazwa_pypi(self):
        from pobieracz import pobierz_licencje

        wynik = pobierz_licencje("../evil", "pypi")
        self.assertFalse(wynik.sukces)
        self.assertIsNotNone(wynik.blad)

    def test_pobierz_licencje_nieprawidlowa_nazwa_npm(self):
        from pobieracz import pobierz_licencje

        wynik = pobierz_licencje("../etc/passwd", "npm")
        self.assertFalse(wynik.sukces)
        self.assertIsNotNone(wynik.blad)

    def test_pobierz_licencje_pypi_mock(self):
        """Sprawdza parsowanie odpowiedzi PyPI API bez połączenia sieciowego."""
        from pobieracz import pobierz_licencje_pypi

        odpowiedz_json = {
            "info": {
                "license_expression": "MIT",
                "license": "MIT License",
                "classifiers": [],
                "version": "2.31.0",
            }
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = odpowiedz_json
        mock_resp.raise_for_status.return_value = None

        with patch("pobieracz.requests.get", return_value=mock_resp), \
             patch("pobieracz._pobierz_z_cache", return_value=None), \
             patch("pobieracz._zapisz_cache"):
            wynik = pobierz_licencje_pypi("requests", "2.31.0")

        self.assertTrue(wynik.sukces)
        self.assertEqual(wynik.licencja_surowa, "MIT")
        self.assertEqual(wynik.wersja, "2.31.0")
        self.assertEqual(wynik.ekosystem, "pypi")

    def test_pobierz_licencje_npm_mock(self):
        """Sprawdza parsowanie odpowiedzi npm Registry bez połączenia sieciowego."""
        from pobieracz import pobierz_licencje_npm

        odpowiedz_json = {"license": "ISC", "version": "4.18.2"}
        mock_resp = MagicMock()
        mock_resp.json.return_value = odpowiedz_json
        mock_resp.raise_for_status.return_value = None

        with patch("pobieracz.requests.get", return_value=mock_resp), \
             patch("pobieracz._pobierz_z_cache", return_value=None), \
             patch("pobieracz._zapisz_cache"):
            wynik = pobierz_licencje_npm("express", "4.18.2")

        self.assertTrue(wynik.sukces)
        self.assertEqual(wynik.licencja_surowa, "ISC")
        self.assertEqual(wynik.wersja, "4.18.2")
        self.assertEqual(wynik.ekosystem, "npm")

    def test_pobierz_licencje_pypi_blad_http_404(self):
        """Sprawdza obsługę błędu 404 z PyPI."""
        import requests as req
        from pobieracz import pobierz_licencje_pypi

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        error = req.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = error

        with patch("pobieracz.requests.get", return_value=mock_resp), \
             patch("pobieracz._pobierz_z_cache", return_value=None):
            wynik = pobierz_licencje_pypi("nieistniejacy-pakiet")

        self.assertFalse(wynik.sukces)
        self.assertIsNotNone(wynik.blad)

    def test_pobierz_licencje_pypi_blad_sieci(self):
        """Sprawdza obsługę błędu połączenia sieciowego."""
        import requests as req
        from pobieracz import pobierz_licencje_pypi

        with patch(
            "pobieracz.requests.get",
            side_effect=req.exceptions.ConnectionError("brak sieci"),
        ), patch("pobieracz._pobierz_z_cache", return_value=None):
            wynik = pobierz_licencje_pypi("requests")

        self.assertFalse(wynik.sukces)
        self.assertIn("sieci", wynik.blad.lower())


# ---------------------------------------------------------------------------
# Testy doradcy LLM
# ---------------------------------------------------------------------------


class TestDoradcaLLM(unittest.TestCase):
    """Testy modułu budowania promptów i wczytywania opisu projektu."""

    def _stworz_wynik_analizy(self):
        from analizator import analizuj_zaleznie
        from skaner import Zaleznosc
        from pobieracz import WynikPobierania

        zaleznie = [
            Zaleznosc("requests", "2.31.0", "pypi", "req.txt"),
            Zaleznosc("gpl-lib", "1.0", "pypi", "req.txt"),
        ]
        wyniki = [
            WynikPobierania("requests", "2.31.0", "pypi", "MIT", "https://pypi.org/"),
            WynikPobierania("gpl-lib", "1.0", "pypi", "GPL-3.0", "https://pypi.org/"),
        ]
        return analizuj_zaleznie(zaleznie, wyniki)

    def test_buduj_prompt_zawiera_liczbe_zaleznie(self):
        from doradca_llm import _buduj_prompt_uzytkownika

        wynik = self._stworz_wynik_analizy()
        prompt = _buduj_prompt_uzytkownika("Opis testowego projektu.", wynik)
        self.assertIn("2", prompt)
        self.assertIn("Opis testowego projektu.", prompt)

    def test_buduj_prompt_zawiera_gpl(self):
        from doradca_llm import _buduj_prompt_uzytkownika

        wynik = self._stworz_wynik_analizy()
        prompt = _buduj_prompt_uzytkownika("Projekt testowy.", wynik)
        # Prompt powinien wspominać licencje silnego copyleft
        self.assertIn("GPL", prompt)

    def test_buduj_prompt_jest_stringiem(self):
        from doradca_llm import _buduj_prompt_uzytkownika

        wynik = self._stworz_wynik_analizy()
        prompt = _buduj_prompt_uzytkownika("Test.", wynik)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)

    def test_pobierz_opis_projektu_readme_istnieje(self):
        from doradca_llm import _pobierz_opis_projektu

        with tempfile.TemporaryDirectory() as tmpdir:
            katalog = Path(tmpdir)
            readme = katalog / "README.md"
            readme.write_text("# Testowy projekt\n\nOpis projektu.", encoding="utf-8")
            opis = _pobierz_opis_projektu(katalog)
            self.assertIn("Testowy projekt", opis)

    def test_pobierz_opis_projektu_brak_readme(self):
        from doradca_llm import _pobierz_opis_projektu

        with tempfile.TemporaryDirectory() as tmpdir:
            katalog = Path(tmpdir)
            opis = _pobierz_opis_projektu(katalog)
            # Powinien zwrócić domyślny opis zamiast rzucić wyjątek
            self.assertIsInstance(opis, str)
            self.assertGreater(len(opis), 0)

    def test_pobierz_opis_projektu_obcina_do_2000_znakow(self):
        from doradca_llm import _pobierz_opis_projektu

        with tempfile.TemporaryDirectory() as tmpdir:
            katalog = Path(tmpdir)
            readme = katalog / "README.md"
            readme.write_text("x" * 5000, encoding="utf-8")
            opis = _pobierz_opis_projektu(katalog)
            self.assertLessEqual(len(opis), 2000)


# ---------------------------------------------------------------------------
# Testy raportu — sortowanie i generowanie HTML
# ---------------------------------------------------------------------------


class TestRaportDodatkowe(unittest.TestCase):
    """Testy sortowania po ryzyku i generowania raportu HTML."""

    def _stworz_analizy(self):
        from analizator import analizuj_zaleznie
        from skaner import Zaleznosc
        from pobieracz import WynikPobierania

        zaleznie = [
            Zaleznosc("mit-lib", "1.0", "pypi", "req.txt"),
            Zaleznosc("gpl-lib", "1.0", "pypi", "req.txt"),
            Zaleznosc("apache-lib", "1.0", "pypi", "req.txt"),
            Zaleznosc("nieznana-lib", "1.0", "pypi", "req.txt"),
        ]
        wyniki = [
            WynikPobierania("mit-lib", "1.0", "pypi", "MIT", "https://pypi.org/"),
            WynikPobierania("gpl-lib", "1.0", "pypi", "GPL-3.0", "https://pypi.org/"),
            WynikPobierania("apache-lib", "1.0", "pypi", "Apache-2.0", "https://pypi.org/"),
            WynikPobierania("nieznana-lib", "1.0", "pypi", None, "https://pypi.org/"),
        ]
        return analizuj_zaleznie(zaleznie, wyniki)

    def test_filtr_sort_by_risk_kolejnosc(self):
        from raport import _filtr_sort_by_risk
        from licencje import PoziomRyzyka

        wynik_analizy = self._stworz_analizy()
        posortowane = _filtr_sort_by_risk(wynik_analizy.zaleznie_analizy)

        # Silne copyleft powinny być pierwsze
        self.assertEqual(posortowane[0].poziom_ryzyka, PoziomRyzyka.SILNE_COPYLEFT)

    def test_filtr_sort_by_risk_zachowuje_wszystkie(self):
        from raport import _filtr_sort_by_risk

        wynik_analizy = self._stworz_analizy()
        posortowane = _filtr_sort_by_risk(wynik_analizy.zaleznie_analizy)
        self.assertEqual(len(posortowane), 4)

    def _generuj_html_do_pliku(self, wynik_analizy, nazwa_projektu="Projekt Testowy"):
        """Pomocnik: generuje HTML do pliku tymczasowego, zwraca treść i ścieżkę."""
        from raport import generuj_raport_html

        sciezka = Path(tempfile.mktemp(suffix=".html"))
        generuj_raport_html(wynik_analizy, sciezka, nazwa_projektu)
        return sciezka.read_text(encoding="utf-8"), sciezka

    def test_generuj_raport_html_zwraca_plik_html(self):
        wynik_analizy = self._stworz_analizy()
        html, sciezka = self._generuj_html_do_pliku(wynik_analizy)
        try:
            self.assertIn("<!DOCTYPE html>", html)
        finally:
            sciezka.unlink(missing_ok=True)

    def test_generuj_raport_html_zawiera_nazwy_pakietow(self):
        wynik_analizy = self._stworz_analizy()
        html, sciezka = self._generuj_html_do_pliku(wynik_analizy)
        try:
            self.assertIn("mit-lib", html)
            self.assertIn("gpl-lib", html)
            self.assertIn("apache-lib", html)
        finally:
            sciezka.unlink(missing_ok=True)

    def test_generuj_raport_html_zawiera_nazwe_projektu(self):
        wynik_analizy = self._stworz_analizy()
        html, sciezka = self._generuj_html_do_pliku(wynik_analizy, "Mój Testowy Projekt")
        try:
            self.assertIn("Mój Testowy Projekt", html)
        finally:
            sciezka.unlink(missing_ok=True)

    def test_generuj_raport_html_zapisuje_do_pliku(self):
        from raport import generuj_raport_html

        wynik_analizy = self._stworz_analizy()
        sciezka = Path(tempfile.mktemp(suffix=".html"))
        try:
            generuj_raport_html(wynik_analizy, sciezka, "Projekt")
            tresc = sciezka.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", tresc)
            self.assertGreater(len(tresc), 1000)
        finally:
            sciezka.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
