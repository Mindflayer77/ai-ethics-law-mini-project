# Dokumentacja procesu

Ten plik dokumentuje **jak** pracowałem nad mini-projektem — jakie narzędzia AI wykorzystałem, jakie prompty pisałem, jakie decyzje podjąłem i co nie zadziałało.

> **PROCESS.md jest tak samo ważny jak kod.** Prowadzący ocenia świadome korzystanie z narzędzi AI — to jest kurs o aspektach AI.

---

## Narzędzia AI

[Lista narzędzi AI użytych w projekcie]

| Narzędzie | Do czego używałem |
|-----------|-------------------|
| Github Copilot - Claude Sonnet 4.6 wysoki reasoning w trybie agentowym | Generowanie struktury repozytorium, generowanie wstępnych opisów licencji i analizy kompatybilności między licencjami  |
| Google Gemini 3 Pro - reasoning | Dokładniejsza analiza licencji i weryfikacja błędów (na podstawie źródeł) a także uzupełnianie rekomendacji wyświetlanych w przypadku wykrycia konfliktów|
|OpenAI GPT-4.1 nano| Wykorzystany do generowania przykładowych sugestii dotyczących licencji na podstawie raportów repozytoriów takich jak transformers czy nextjs|

## Prompty

> Nie wklejaj outputu z AI — tylko prompty, które wpisywałeś/aś.

### [Kategoria 1 "Generowanie kodu"]
Poniżej przedstawiony został prompt zastosowany do modelu Claude Sonnet 4.6 z włączonym wysokim reasoningiem w trybie agentowym służący do stworzenia pierwszej wersi projektu. Jako konktekst dla modelu załączony został również plik project_description.txt w którym opisane były wymagania projektowe, a także załączone były źródła opisów licencji, z których model powinien korzystać.
```
Twoim zadaniem jest stworzenie skryptu / systemu który pozwoli skanować zależności projektów oraz analizwać ich licencje. Dokładny opis projektu znajduje się w pliku project_description.txt. Instrukcje dla ciebie czyli agenta znajdują się w pliku AGENTS.md. Zadbaj o wysoką jakość tworzonego projektu.
```

**Kontekst:** Chciałem sprawdzić jak dobrze poradzi sobie model z generacją projektu oraz opisami poszczególnych licencji, zakładając z góry że prawdopodobnie będą niezbędne poprawki. Żeby zakorzenić wiedzę o licencjach modelu w prawdziwej wiedzy i zmniejszenie halucynacji, załączone zostały wstępnie ręcznie wyszukane źródła zawierające opisy licencji.

Następny prompt dotyczył poprawek w generownaym kodzie takich jak błędy w renderowanym HTML oraz literówki.
```
Popraw generowanie raportu html: W sekcjach 'Słabe copyleft' i 'Własnościowe' nie wyświetlają się poprawnie cyfry. Również po kliknięciu w nazwę danej biblioteki, chcę mieć odniesienie do głównej strony pakietu a nie do metadanych w pliku json. Również chcę aby opisy licencji były wyświetlane w pełni w raporcie, w tym momencie tekst jest ucinany, a chcę żeby był w pełni widoczny.  Ponadto popraw literówki w generowanym raporcie .json takie jak 'liczba_zaleznie' czy 'zalezne'. Nie zmieniaj pozostałych informacji takich jak opisy licencji czy rekomendacje.
```

**Kontekst:** Małe błędy wygenerowanego kodu do poprawienia.

Poniższy prompt został wpisany w celu poprawy błędu licencji pakietu psycopg. Model Claude Sonnet 4.6 Github Copilot.
```
Zweryfikuj skąd powstał problem, że pakiet psycopg został oceniony jako GPL, jednak w opisie licencji mamy License: GNU Library or Lesser General Public License (LGPL) (LGPL with exceptions)  więc wydaje mi się że powinno być LGPL, gdyż pakiet ten został wykryty w bibliotece Transformers która jest na licencji Apache 2.0.
```

**Kontekst:** Model źle odczytał licencje biblioteki ze strony pypi.


Kolejny prompt był napisany w celu poprawy pobierania licencji z npm i pypi.

```
Niektóre biblioteki w wygenerowanych raportach mają ustawioną licencję nieznaną jednak na stronie widnieje licencja MIT jak na przykład tutaj @ast-grep/cli , @base-ui-components/react, lub ISC tutaj https://www.npmjs.com/package/fs lub tutaj kaleido (License: The MIT License (MIT) Copyright (c) Plotly, Inc Permission is hereby granted, free of charge, to a... ). Zweryfikuj jeszcze raz wszystkie licencje z wygenerowanych raportów, które zostały oznaczone jako Nieznane i popraw jak najwięcej błędów.
```

**Kontekst:** Model zwracał bardzo dużo licencji jako 'Nieznane', zwłaszcza z rejestru npn. Po ręcznej weryfikacji okazało się że jest to błąd z pobieraniem licencji przez skrypt, zostało to poprawione dzięki przedstawieniu modelowi konkretnych przypadków błędu.

Poniższy prompt służył dodaniu funkcjonalności przeszukiwania repozytorium tylko na określony poziom wgłąb

```
Dodaj parametr --depth oraz możliwość wyboru, jak głęboko skrypt będzie skanował w poszukiwaniu zależności.
```

**Kontekst:** Chciałem żeby użytkownik mógł wybrać czy chce skanować cały projekt czy tylko jego górną część (na przykład w przypadku tego repozytorium pobrałem kilka repozytoriów do katalogu tmp/ i kiedy chcę przeskanować zależnosci tylko mojego głównego projektu ustawiam --depth 0)

Poniższy prompt został wywołany po wszystkich modyfikacjach kodu, aby zapewnić odpowiednie pokrycie testami.

```
Zaaktualizuj testy, usuń niepotrzebne testy wykorzystujące example_openai example _anthropic i example_gemini oraz uzupełnij o nowe testy niezbędne do weryfikacji kodu projektu.
```

**Kontekst:** Chciałem żeby zapewnione zostało odpowiednie pokrycie kodu testami, dzięki czemu zmniejszamy ryzyko wystąpienia błędów podczas gdy stworzona biblioteka będzie wykorzystywana przez użytkowników. 

### [Kategoria 2 Weryfikacja opisów licencji oraz kompatybilności]

Poniżej przedstawiony został prompt wykorzystany do weryfikacji opisów licencji znajdujących się w pliku src/licencje.py. Prompt został wpisany do modelu Gemini 3 Pro reasoning.
```
Zweryfikuj opisy licencji przedstawione w tym pliku i na podstawie poniższych źródeł popraw wszelkie nieścisłości:

- https://choosealicense.com/appendix/

- https://spdx.org/licenses/

- https://www.tldrlegal.com/

- https://opensource.org/licenses

- https://www.gnu.org/licenses/license-compatibility.html 
```

**Kontekst:** Chciałem żeby drugi niezaleźny model zweryfikował opisy przygotowane przez pierwszego agenta i wyłapał ewentualne nieścisłości. Z racji że modele mają tendencję do halucynacji, tutaj również załączyłem źródła na podstawie których powinien się wzorować.

To samo co powyżej zostało również wykonane załączając plik src/analizator.py aby zweryfikowane i poprawione zostały rekomendacje dla użytkownika.

```
 Przeanalizuj rekomendacje przedstawione w tym pliku, które prezentowane są użytkownikowi w zależności od wykrytych licencji w projekcie, a następnie na podstawie poniższych źródeł popraw ewentualne błędy oraz dodaj własne rekomendacje jeśli czegoś brakuje. Źródła:

- https://choosealicense.com/appendix/

- https://spdx.org/licenses/

- https://www.tldrlegal.com/

- https://opensource.org/licenses

- https://www.gnu.org/licenses/license- 
```

**Kontekst:** Tutaj również chciałem żeby rekomendacje były bardziej rzetelne i dokładniejsze, dlatego przeprowadziłem kolejną weryfikację z wykrozystaniem modelu językowego.

## Decyzje

[Kluczowe decyzje podjęte w trakcie pracy]

1. **Weryfikacja i poprawa opisów licencji, kompatybilności oraz rekomendacji** — Decyzja ta była podjęta w celu zapewnienia bardziej rzetelnych opisów licencji wygenerowanych przez pierwszego agenta. Decyzję podjąłem gdyż nie pierwszy raz spotykam się z problemem halucynacji modeli językowych i byłem prawie pewien że tutaj również mógł się pojawić taki problem. 

2. **Weryfikacja działania skryptu na kilku repozytoriach** - niezbędna decyzja do sprawdzenia czy skrypty radzą sobie w różnych typach repozytoriów czy tylko zadziałały na małych repozytoriach.

2. **Ręczna weryfikacja przypadków Nieznanych licencji** - podejrzane wydało mi się, że w przypadku większych repozytoriów tak dużo bibliotek jest zwracanych jako 'Nieznane', dlatego przeprowadziłem ręczną weryfikację kilku przypadków w celu zweryfikowania czy nie jest to błąd w działaniu skryptu. 

## Co nie zadziałało

1. **Małe błędy w generowaniu raportu** — generowany był niedokładny raport html, gdzie niektóre liczby licencji nie wyświetlały się, a także w raporcie typu json były literówki. Poprawione zostało poprzez dodatkowy refinement z wykorzystaniem tego samego agenta co generował początkowo kod.

2. **Niescisłości w opisach licencji** - po weryfikacji z wykorzystaniem silnego modelu Gemini 3 Pro oraz źródeł, wykryte zostało kilka niescisłości we wstępnie wygenerowanych opisach licencji a także opisach kompatybilności. Poprawione zostało poprzez analizę rezultatów otrzymanych przez Gemini. 

2. **Skrypt źle zweryfikował licencję pakietu psycopg2** — Skrypt źle scrapował informacje z ze strony pypi i przypisywał do pakietu licencję GPL zamiast LGPL. Poprawione poprzez dodatkowy prompt do agenta z podaniem tego konkretnego przypadku błedu.

3. **Złe pobieranie licencji** - wstępny skrypt ignorował licencje o opisach > 100 znaków (biblioteki takie jak kaleido czy amdsmi mają pełny tekst licencji MIT), a także nie obsługiwał starszego formatu opisu licencji npm [{"type": "MIT"}] zamiast "license": "MIT".
Po poprawkach skrypt wykrywa słowa kluczowe takie jak MIT, Apache, BSD itd. a także obsługuje obydwa formaty npm. Również powstał słownik _ZNANE_LICENCJE_FALLBACK, który zaweria zweryfikowane przez agenta licencje (poprzez wyszukiwanie z dostępem do przgeglądarki a nie tylko poprzez API) dla przypadków gdzie API nie zwraca danych licencyjnych.

## Iteracje

[Jak projekt ewoluował? Krótki opis kolejnych wersji / podejść]

1. **v1** - Pierwsza wersja wygenerowanych skryptów - obiecujące wyniki ale kilka błędów.

2. **v2** - Zaaktualizowanie opisów licencji oraz opisów kompatybilności żeby zwiększyć rzetelność generowanego raportu.

3. **v3** - Poprawki w wygenerowanym kodzie oraz w sposobie pobierania licencji.

4. **v4** - Uzupełnienie testów po wszystkich zmianach kodu, aby zapewnić jak największą odporność na ewentlualne błędy.

5. **v5** - Wersja finalna po stworzeniu raportu oraz zaaktualizowaniu README.md 


