"""
Generator raportów audytu licencji.

Obsługuje następujące formaty wyjściowe:
- HTML: pełny raport z wizualizacją (wykres kołowy SVG, kolorowane tabele)
- JSON: dane maszynowo czytelne
- Tekst: prosty raport terminalkowy

Raport HTML jest samodzielnym plikiem (standalone) — nie wymaga
zewnętrznych zasobów (CSS/JS CDN) dla bezpieczeństwa.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, BaseLoader

from analizator import WynikAnalizy, ZaleznoscAnaliza, KonfliktLicencji, generuj_rekomendacje
from licencje import PoziomRyzyka


# ---------------------------------------------------------------------------
# Szablon HTML (samodzielny, inline CSS)
# ---------------------------------------------------------------------------

_SZABLON_HTML = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Raport audytu licencji — {{ nazwa_projektu }}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      line-height: 1.6;
    }
    /* Nagłówek */
    header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      color: #fff;
      padding: 2.5rem 2rem 2rem;
    }
    header h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 0.3rem; }
    header .meta { font-size: 0.88rem; opacity: 0.75; }
    header .meta span { margin-right: 1.5rem; }
    /* Kontener główny */
    .container { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }
    /* Karty podsumowania */
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .card {
      background: #fff;
      border-radius: 10px;
      padding: 1.2rem 1.4rem;
      box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      border-left: 4px solid var(--kolor);
    }
    .card .liczba { font-size: 2.2rem; font-weight: 800; color: var(--kolor); line-height: 1; }
    .card .etykieta { font-size: 0.82rem; color: #666; margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.05em; }
    /* Sekcja wykresu + legendy */
    .wizualizacja {
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 2rem;
      align-items: center;
      background: #fff;
      border-radius: 10px;
      padding: 1.8rem 2rem;
      box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      margin-bottom: 2rem;
    }
    @media (max-width: 680px) { .wizualizacja { grid-template-columns: 1fr; } }
    .wykres-tytul { font-size: 1.1rem; font-weight: 700; margin-bottom: 1.2rem; }
    .legenda { list-style: none; }
    .legenda li {
      display: flex;
      align-items: center;
      gap: 0.7rem;
      padding: 0.45rem 0;
      border-bottom: 1px solid #f0f0f0;
      font-size: 0.9rem;
    }
    .legenda li:last-child { border-bottom: none; }
    .legenda .kolor-krotka {
      width: 14px;
      height: 14px;
      border-radius: 3px;
      flex-shrink: 0;
    }
    .legenda .proc { margin-left: auto; font-weight: 600; }
    /* Tabele */
    .sekcja {
      background: #fff;
      border-radius: 10px;
      padding: 1.8rem 2rem;
      box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      margin-bottom: 2rem;
    }
    .sekcja h2 {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 1.2rem;
      padding-bottom: 0.6rem;
      border-bottom: 2px solid #f0f0f0;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    thead tr { background: #f8f9fa; }
    thead th {
      padding: 0.7rem 1rem;
      text-align: left;
      font-weight: 600;
      color: #555;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      border-bottom: 2px solid #e9ecef;
    }
    tbody tr { border-bottom: 1px solid #f0f2f5; transition: background 0.15s; }
    tbody tr:hover { background: #f8f9fa; }
    tbody td { padding: 0.7rem 1rem; vertical-align: top; }
    .td-opis { color: #555; font-size: 0.82rem; line-height: 1.5; word-wrap: break-word; min-width: 200px; }
    /* Odznaki ryzyka */
    .badge {
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .badge-bezpieczna    { background: #d5f5e3; color: #1e8449; }
    .badge-slabe_copyleft { background: #fef9e7; color: #9a7d0a; }
    .badge-silne_copyleft { background: #fdedec; color: #c0392b; }
    .badge-wlascnosci    { background: #f5eef8; color: #7d3c98; }
    .badge-nieznana      { background: #f2f3f4; color: #5d6d7e; }
    /* Konflikty */
    .konflikt-karta {
      border: 1px solid #f5c6cb;
      border-radius: 8px;
      padding: 1rem 1.2rem;
      margin-bottom: 1rem;
      background: #fff5f5;
    }
    .konflikt-karta .naglowek {
      font-weight: 700;
      color: #c0392b;
      margin-bottom: 0.4rem;
      font-size: 0.95rem;
    }
    .konflikt-karta .opis { font-size: 0.85rem; color: #555; }
    /* Rekomendacje */
    .rekomendacja {
      padding: 0.85rem 1.1rem;
      border-radius: 7px;
      margin-bottom: 0.8rem;
      font-size: 0.88rem;
      line-height: 1.6;
      border-left: 4px solid;
    }
    .rek-ok      { background: #d5f5e3; border-color: #2ecc71; color: #1e8449; }
    .rek-info    { background: #eaf4fb; border-color: #3498db; color: #1a5276; }
    .rek-uwaga   { background: #fef9e7; border-color: #f39c12; color: #9a7d0a; }
    .rek-blad    { background: #fdedec; border-color: #e74c3c; color: #922b21; }
    /* Stopka */
    footer {
      text-align: center;
      padding: 1.5rem;
      font-size: 0.8rem;
      color: #999;
    }
    /* Link */
    a { color: #0f3460; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .pakiet-link { font-weight: 600; }
    .emoji { font-style: normal; }
    /* Stan: brak danych */
    .brak-danych { text-align: center; padding: 2rem; color: #aaa; font-size: 0.9rem; }
  </style>
</head>
<body>

<header>
  <h1>🔍 Raport audytu licencji</h1>
  <div class="meta">
    <span>📁 Projekt: <strong>{{ nazwa_projektu }}</strong></span>
    <span>📅 Data: {{ data_skanowania }}</span>
    <span>📦 Zależności: {{ wynik.liczba_zaleznie }}</span>
    {% if wynik.ma_wysokie_ryzyko %}
    <span style="color:#ff6b6b; font-weight:700;">⚠️ Wykryto problemy licencyjne!</span>
    {% else %}
    <span style="color:#6bff6b; font-weight:700;">✅ Brak krytycznych problemów</span>
    {% endif %}
  </div>
</header>

<div class="container">

  <!-- Karty podsumowania -->
  <div class="cards">
    <div class="card" style="--kolor: #2ecc71">
      <div class="liczba">{{ wynik.statystyki_ryzyka['bezpieczna'] }}</div>
      <div class="etykieta">Bezpieczne (permissive)</div>
    </div>
    <div class="card" style="--kolor: #f39c12">
      <div class="liczba">{{ wynik.statystyki_ryzyka['slabe_copyleft'] }}</div>
      <div class="etykieta">Słabe copyleft</div>
    </div>
    <div class="card" style="--kolor: #e74c3c">
      <div class="liczba">{{ wynik.statystyki_ryzyka['silne_copyleft'] }}</div>
      <div class="etykieta">Silne copyleft (GPL/AGPL)</div>
    </div>
    <div class="card" style="--kolor: #9b59b6">
      <div class="liczba">{{ wynik.statystyki_ryzyka['wlasnosci'] }}</div>
      <div class="etykieta">Własnościowe</div>
    </div>
    <div class="card" style="--kolor: #95a5a6">
      <div class="liczba">{{ wynik.statystyki_ryzyka['nieznana'] }}</div>
      <div class="etykieta">Nieznane</div>
    </div>
    <div class="card" style="--kolor: #e74c3c">
      <div class="liczba">{{ wynik.konflikty|length }}</div>
      <div class="etykieta">Konflikty licencji</div>
    </div>
  </div>

  <!-- Wizualizacja: wykres + legenda -->
  <div class="wizualizacja">
    <div>
      <div class="wykres-tytul">Profil ryzyka licencyjnego</div>
      {{ wykres_svg | safe }}
    </div>
    <div>
      <ul class="legenda">
        {% for poz, kolor, etykieta, liczba, proc in legenda %}
        <li>
          <span class="kolor-krotka" style="background:{{ kolor }}"></span>
          <span>{{ etykieta }}</span>
          <span class="proc">{{ liczba }} ({{ proc }}%)</span>
        </li>
        {% endfor %}
      </ul>
    </div>
  </div>

  <!-- Rekomendacje -->
  <div class="sekcja">
    <h2>📋 Rekomendacje</h2>
    {% for rek in rekomendacje %}
    {% set klasa = 'rek-ok' if rek.startswith('✅') else ('rek-uwaga' if rek.startswith('⚠️') or rek.startswith('ℹ️') else ('rek-blad' if rek.startswith('⛔') or rek.startswith('⚠️') else 'rek-info')) %}
    <div class="rekomendacja {{ klasa }}">{{ rek }}</div>
    {% endfor %}
  </div>

  <!-- Konflikty -->
  {% if wynik.konflikty %}
  <div class="sekcja">
    <h2>⚡ Konflikty kompatybilności licencji</h2>
    {% for konflikt in wynik.konflikty %}
    <div class="konflikt-karta">
      <div class="naglowek">
        {{ konflikt.pakiet_a }}
        <span class="badge badge-{{ konflikt.licencja_a | licencja_badge }}">{{ konflikt.licencja_a }}</span>
        ↔
        {{ konflikt.pakiet_b }}
        <span class="badge badge-{{ konflikt.licencja_b | licencja_badge }}">{{ konflikt.licencja_b }}</span>
      </div>
      <div class="opis">{{ konflikt.opis }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Lista zależności -->
  <div class="sekcja">
    <h2>📦 Lista zależności ({{ wynik.liczba_zaleznie }})</h2>
    {% if wynik.zaleznie_analizy %}
    <table>
      <thead>
        <tr>
          <th>Pakiet</th>
          <th>Wersja</th>
          <th>Ekosystem</th>
          <th>Licencja</th>
          <th>Ryzyko</th>
          <th>Opis licencji</th>
        </tr>
      </thead>
      <tbody>
        {% for analiza in wynik.zaleznie_analizy | sort_by_risk %}
        <tr>
          <td>
            <a class="pakiet-link"
               href="{% if analiza.zaleznosc.ekosystem == 'pypi' %}https://pypi.org/project/{{ analiza.zaleznosc.nazwa }}/{% else %}https://www.npmjs.com/package/{{ analiza.zaleznosc.nazwa }}{% endif %}"
               target="_blank"
               rel="noopener noreferrer">
              {{ analiza.zaleznosc.nazwa }}
            </a>
          </td>
          <td>{{ analiza.wynik_pobierania.wersja or analiza.zaleznosc.wersja or "—" }}</td>
          <td>
            <span class="badge" style="background:#e8f4f8;color:#2980b9;">
              {{ analiza.zaleznosc.ekosystem }}
            </span>
          </td>
          <td>
            {% if analiza.info_licencji %}
            <a href="{{ analiza.info_licencji.link_spdx }}"
               target="_blank" rel="noopener noreferrer"
               title="{{ analiza.info_licencji.nazwa }}">
              {{ analiza.nazwa_licencji_do_wyswietlenia }}
            </a>
            {% else %}
            {{ analiza.nazwa_licencji_do_wyswietlenia }}
            {% endif %}
          </td>
          <td>
            <span class="badge badge-{{ analiza.poziom_ryzyka.value | replace('ę','e') | replace('ó','o') | replace('ś','s') | replace('ł','l') | replace('ą','a') | replace('ź','z') | replace('ż','z') | replace('ć','c') | replace('ń','n') | normalize_badge }}">
              {{ analiza.poziom_ryzyka.etykieta }}
            </span>
          </td>
          <td class="td-opis">{{ analiza.opis_licencji }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="brak-danych">Nie znaleziono żadnych zależności.</div>
    {% endif %}
  </div>

  <!-- Źródła plików -->
  <div class="sekcja">
    <h2>📂 Przeskanowane pliki manifestowe</h2>
    <ul style="padding-left:1.2rem; font-size:0.88rem; color:#555; line-height:2">
      {% for plik in pliki_zrodlowe %}
      <li><code>{{ plik }}</code></li>
      {% endfor %}
      {% if not pliki_zrodlowe %}
      <li style="list-style:none; color:#aaa">Brak danych o plikach źródłowych.</li>
      {% endif %}
    </ul>
  </div>

</div>

<footer>
  Wygenerowano przez <strong>audyt-licencji</strong> |
  Mini-projekt: Aspekty prawne, społeczne i etyczne w AI | PWr 2025/2026 |
  {{ data_skanowania }}
</footer>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Generowanie wykresu SVG (kołowy donut)
# ---------------------------------------------------------------------------


def _generuj_donut_svg(
    wartosci: dict[str, tuple[float, str]],
    promien_zewn: int = 100,
    grubosc: int = 38,
) -> str:
    """
    Generuje SVG z wykresem donut na podstawie procentowych wartości.

    Args:
        wartosci: Słownik {etykieta: (procent, kolor_hex)}
        promien_zewn: Zewnętrzny promień okręgu.
        grubosc: Grubość pierścienia.

    Returns:
        Fragment SVG jako string.
    """
    cx = cy = promien_zewn + 10
    r = promien_zewn - grubosc // 2
    obwod = 2 * math.pi * r

    fragmenty: list[str] = []
    offset = 0.0

    for etykieta, (procent, kolor) in wartosci.items():
        if procent <= 0:
            continue
        dl_luku = procent / 100.0 * obwod
        przerwa = obwod - dl_luku
        # stroke-dashoffset obraca punkt startowy o -90° (góra)
        dashoffset = -(offset / 100.0 * obwod) + obwod * 0.25
        fragmenty.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{kolor}" stroke-width="{grubosc}" '
            f'stroke-dasharray="{dl_luku:.2f} {przerwa:.2f}" '
            f'stroke-dashoffset="{dashoffset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})">'
            f'<title>{etykieta}: {procent:.1f}%</title>'
            f"</circle>"
        )
        offset += procent

    rozmiar = (promien_zewn + 10) * 2
    svg = (
        f'<svg width="{rozmiar}" height="{rozmiar}" viewBox="0 0 {rozmiar} {rozmiar}" '
        f'xmlns="http://www.w3.org/2000/svg">'
    )
    if not fragmenty:
        # Pusty okrąg
        svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#eee" stroke-width="{grubosc}"/>'
    else:
        svg += "".join(fragmenty)
    # Środkowy tekst
    total_text = sum(v for v, _ in wartosci.values())
    svg += (
        f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" '
        f'font-size="28" font-weight="800" fill="#1a1a2e">'
        f'{int(round(total_text))}</text>'
        f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" '
        f'font-size="12" fill="#888">dep.</text>'
    )
    svg += "</svg>"
    return svg


# ---------------------------------------------------------------------------
# Filtry Jinja2
# ---------------------------------------------------------------------------


def _filtr_normalize_badge(wartosc: str) -> str:
    """
    Konwertuje wartość PoziomRyzyka.value na klasę CSS badge.
    Uwaga: wartości mogą zawierać polskie znaki.
    """
    mapowanie = {
        "bezpieczna": "bezpieczna",
        "s\u0142abe_copyleft": "slabe_copyleft",
        "silne_copyleft": "silne_copyleft",
        "w\u0142a\u015bno\u015bciowa": "wlascnosci",
        "nieznana": "nieznana",
    }
    return mapowanie.get(wartosc.lower(), "nieznana")


def _filtr_licencja_badge(licencja: str) -> str:
    """Zwraca klasę CSS badge dla danej licencji SPDX."""
    from licencje import pobierz_info_licencji, normalizuj_nazwe_licencji, PoziomRyzyka

    spdx = normalizuj_nazwe_licencji(licencja)
    info = pobierz_info_licencji(spdx) if spdx else None
    if not info:
        return "nieznana"
    mapowanie = {
        PoziomRyzyka.BEZPIECZNA: "bezpieczna",
        PoziomRyzyka.SLABE_COPYLEFT: "slabe_copyleft",
        PoziomRyzyka.SILNE_COPYLEFT: "silne_copyleft",
        PoziomRyzyka.WLASNOSCI: "wlascnosci",
        PoziomRyzyka.NIEZNANA: "nieznana",
    }
    return mapowanie.get(info.poziom_ryzyka, "nieznana")


def _filtr_sort_by_risk(analizy: list[ZaleznoscAnaliza]) -> list[ZaleznoscAnaliza]:
    """Sortuje zależności: najpierw najgroźniejsze."""
    porzadek = {
        PoziomRyzyka.SILNE_COPYLEFT: 0,
        PoziomRyzyka.WLASNOSCI: 1,
        PoziomRyzyka.NIEZNANA: 2,
        PoziomRyzyka.SLABE_COPYLEFT: 3,
        PoziomRyzyka.BEZPIECZNA: 4,
    }
    return sorted(analizy, key=lambda a: (porzadek.get(a.poziom_ryzyka, 5), a.zaleznosc.nazwa.lower()))


# ---------------------------------------------------------------------------
# Główne funkcje generowania raportów
# ---------------------------------------------------------------------------


def generuj_raport_html(
    wynik: WynikAnalizy,
    sciezka_wyjscia: Path,
    nazwa_projektu: str = "Projekt",
) -> None:
    """
    Generuje pełny raport HTML audytu licencji.

    Args:
        wynik: Wynik analizy zależności.
        sciezka_wyjscia: Ścieżka pliku wyjściowego HTML.
        nazwa_projektu: Nazwa projektu (dla tytułu).
    """
    env = Environment(loader=BaseLoader(), autoescape=True)
    env.filters["normalize_badge"] = _filtr_normalize_badge
    env.filters["licencja_badge"] = _filtr_licencja_badge
    env.filters["sort_by_risk"] = _filtr_sort_by_risk

    # Dane do wykresu SVG
    stats = wynik.statystyki_ryzyka
    procs = wynik.procenty_ryzyka
    total = wynik.liczba_zaleznie

    dane_wykresu: dict[str, tuple[float, str]] = {}
    konfiguracja_poziomow = [
        (PoziomRyzyka.BEZPIECZNA, "#2ecc71"),
        (PoziomRyzyka.SLABE_COPYLEFT, "#f39c12"),
        (PoziomRyzyka.SILNE_COPYLEFT, "#e74c3c"),
        (PoziomRyzyka.WLASNOSCI, "#9b59b6"),
        (PoziomRyzyka.NIEZNANA, "#95a5a6"),
    ]
    for poz, kolor in konfiguracja_poziomow:
        if stats[poz] > 0:
            dane_wykresu[poz.etykieta] = (procs[poz], kolor)

    wykres_svg = _generuj_donut_svg(dane_wykresu)

    # Legenda
    legenda = [
        (poz, kolor, poz.etykieta, stats[poz], procs[poz])
        for poz, kolor in konfiguracja_poziomow
    ]

    # Rekomendacje
    rekomendacje = generuj_rekomendacje(wynik)

    # Unikalnie pliki źródłowe
    pliki_zrodlowe = sorted(
        set(a.zaleznosc.plik_zrodlowy for a in wynik.zaleznie_analizy)
    )

    # Statystyki per klucz (template-friendly) — klucze ASCII dopasowane do szablonu
    stats_str = {
        "bezpieczna": stats[PoziomRyzyka.BEZPIECZNA],
        "slabe_copyleft": stats[PoziomRyzyka.SLABE_COPYLEFT],
        "silne_copyleft": stats[PoziomRyzyka.SILNE_COPYLEFT],
        "wlasnosci": stats[PoziomRyzyka.WLASNOSCI],
        "nieznana": stats[PoziomRyzyka.NIEZNANA],
    }

    # Renderowanie
    szablon = env.from_string(_SZABLON_HTML)
    html = szablon.render(
        nazwa_projektu=nazwa_projektu,
        data_skanowania=datetime.now().strftime("%Y-%m-%d %H:%M"),
        wynik=wynik,
        wykres_svg=wykres_svg,
        legenda=legenda,
        rekomendacje=rekomendacje,
        pliki_zrodlowe=pliki_zrodlowe,
    )

    # Nadpisz statystyki string w obiekcie wynik dla szablonu
    # (PoziomRyzyka.value → string key w dict)
    # Uwaga: szablon korzysta z wynik.statystyki_ryzyka — musimy mapować
    # PoziomRyzyka.value na ints. Robimy to przez monkey-patching dataclass.
    # Zamiast tego — przekażemy stats_str bezpośrednio.

    # Re-renderuj z stats_str (klucze string dla szablonu)
    html = szablon.render(
        nazwa_projektu=nazwa_projektu,
        data_skanowania=datetime.now().strftime("%Y-%m-%d %H:%M"),
        wynik=_WynikAnalizyDlaTemplatu(wynik, stats_str),
        wykres_svg=wykres_svg,
        legenda=legenda,
        rekomendacje=rekomendacje,
        pliki_zrodlowe=pliki_zrodlowe,
    )

    sciezka_wyjscia.parent.mkdir(parents=True, exist_ok=True)
    sciezka_wyjscia.write_text(html, encoding="utf-8")


class _WynikAnalizyDlaTemplatu:
    """Wrapper dla WynikAnalizy umożliwiający dostęp do statystyk przez string keys w szablonie."""

    def __init__(self, wynik: WynikAnalizy, stats_str: dict[str, int]) -> None:
        self._wynik = wynik
        self._stats_str = stats_str

    @property
    def liczba_zaleznie(self) -> int:
        return self._wynik.liczba_zaleznie

    @property
    def statystyki_ryzyka(self) -> dict[str, int]:
        return self._stats_str

    @property
    def procenty_ryzyka(self) -> dict[str, float]:
        return {poz.value: proc for poz, proc in self._wynik.procenty_ryzyka.items()}

    @property
    def ma_wysokie_ryzyko(self) -> bool:
        return self._wynik.ma_wysokie_ryzyko

    @property
    def ma_nieznane_licencje(self) -> bool:
        return self._wynik.ma_nieznane_licencje

    @property
    def konflikty(self) -> list:
        return self._wynik.konflikty

    @property
    def zaleznie_analizy(self) -> list:
        return self._wynik.zaleznie_analizy


def generuj_raport_json(
    wynik: WynikAnalizy,
    sciezka_wyjscia: Path,
    nazwa_projektu: str = "Projekt",
) -> None:
    """
    Generuje raport JSON — dane maszynowo czytelne.

    Args:
        wynik: Wynik analizy zależności.
        sciezka_wyjscia: Ścieżka pliku wyjściowego JSON.
        nazwa_projektu: Nazwa projektu.
    """
    dane = {
        "projekt": nazwa_projektu,
        "data_skanowania": datetime.now().isoformat(),
        "podsumowanie": {
            "liczba_zaleznosci": wynik.liczba_zaleznie,
            "ma_wysokie_ryzyko": wynik.ma_wysokie_ryzyko,
            "liczba_konfliktow": len(wynik.konflikty),
            "statystyki_ryzyka": {
                poz.value: liczba for poz, liczba in wynik.statystyki_ryzyka.items()
            },
            "procenty_ryzyka": {
                poz.value: proc for poz, proc in wynik.procenty_ryzyka.items()
            },
        },
        "zaleznosci": [
            {
                "nazwa": a.zaleznosc.nazwa,
                "wersja": a.wynik_pobierania.wersja or a.zaleznosc.wersja,
                "ekosystem": a.zaleznosc.ekosystem,
                "plik_zrodlowy": a.zaleznosc.plik_zrodlowy,
                "licencja_spdx": a.licencja_spdx,
                "licencja_surowa": a.wynik_pobierania.licencja_surowa,
                "poziom_ryzyka": a.poziom_ryzyka.value,
                "blad_pobierania": a.wynik_pobierania.blad,
                "url_zrodla": a.wynik_pobierania.url_zrodla,
            }
            for a in wynik.zaleznie_analizy
        ],
        "konflikty": [
            {
                "pakiet_a": k.pakiet_a,
                "licencja_a": k.licencja_a,
                "pakiet_b": k.pakiet_b,
                "licencja_b": k.licencja_b,
                "opis": k.opis,
            }
            for k in wynik.konflikty
        ],
        "rekomendacje": generuj_rekomendacje(wynik),
    }

    sciezka_wyjscia.parent.mkdir(parents=True, exist_ok=True)
    sciezka_wyjscia.write_text(
        json.dumps(dane, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def drukuj_raport_tekstowy(wynik: WynikAnalizy, nazwa_projektu: str = "Projekt") -> str:
    """
    Generuje krótki raport tekstowy do wyświetlenia w terminalu.

    Returns:
        Raport jako string.
    """
    linie: list[str] = []
    sep = "─" * 60

    linie.append(sep)
    linie.append(f"  RAPORT AUDYTU LICENCJI — {nazwa_projektu.upper()}")
    linie.append(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    linie.append(sep)

    stats = wynik.statystyki_ryzyka
    procs = wynik.procenty_ryzyka
    linie.append("")
    linie.append("📊 Podsumowanie:")
    linie.append(f"   Łącznie zależności:    {wynik.liczba_zaleznie}")
    linie.append(f"   ✅ Bezpieczne:          {stats[PoziomRyzyka.BEZPIECZNA]:>3}  ({procs[PoziomRyzyka.BEZPIECZNA]:.1f}%)")
    linie.append(f"   ⚠️  Słabe copyleft:      {stats[PoziomRyzyka.SLABE_COPYLEFT]:>3}  ({procs[PoziomRyzyka.SLABE_COPYLEFT]:.1f}%)")
    linie.append(f"   🔴 Silne copyleft:       {stats[PoziomRyzyka.SILNE_COPYLEFT]:>3}  ({procs[PoziomRyzyka.SILNE_COPYLEFT]:.1f}%)")
    linie.append(f"   🔒 Własnościowe:         {stats[PoziomRyzyka.WLASNOSCI]:>3}  ({procs[PoziomRyzyka.WLASNOSCI]:.1f}%)")
    linie.append(f"   ❓ Nieznane:             {stats[PoziomRyzyka.NIEZNANA]:>3}  ({procs[PoziomRyzyka.NIEZNANA]:.1f}%)")
    linie.append(f"   ⚡ Konflikty:            {len(wynik.konflikty):>3}")
    linie.append("")

    if wynik.konflikty:
        linie.append("⚡ Wykryte konflikty kompatybilności:")
        for k in wynik.konflikty:
            linie.append(f"   • {k.pakiet_a} ({k.licencja_a}) ↔ {k.pakiet_b} ({k.licencja_b})")
        linie.append("")

    linie.append("📦 Zależności wg ryzyka:")
    for analiza in _filtr_sort_by_risk(wynik.zaleznie_analizy):
        ikona = {
            PoziomRyzyka.BEZPIECZNA: "✅",
            PoziomRyzyka.SLABE_COPYLEFT: "⚠️ ",
            PoziomRyzyka.SILNE_COPYLEFT: "🔴",
            PoziomRyzyka.WLASNOSCI: "🔒",
            PoziomRyzyka.NIEZNANA: "❓",
        }.get(analiza.poziom_ryzyka, "  ")
        wer = analiza.wynik_pobierania.wersja or analiza.zaleznosc.wersja or "?"
        lic = analiza.nazwa_licencji_do_wyswietlenia
        linie.append(f"   {ikona} {analiza.zaleznosc.nazwa:<30} {wer:<12} {lic}")

    linie.append("")
    linie.append("📋 Rekomendacje:")
    for rek in generuj_rekomendacje(wynik):
        # Zawija długie linie
        for fragment in [rek[i : i + 100] for i in range(0, len(rek), 100)]:
            linie.append(f"   {fragment}")
        linie.append("")

    linie.append(sep)
    return "\n".join(linie)
