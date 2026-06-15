# System Analizy Meczów Piłki Nożnej (Computer Vision & AI)

Kompleksowy system do automatycznej analizy wideo z meczów piłkarskich oraz wizualizacji statystyk meczowych. Projekt łączy modele widzenia maszynowego (YOLOv8, śledzenie obiektów, transformacja perspektywy) z interaktywnym dashboardem webowym w Shiny for Python.

**Autorzy:** Piotr Zakrzewski, Szymon Marczuk  
**Przedmiot:** Języki skryptowe — Politechnika Wrocławska

---

## Spis treści

1. [Opis projektu](#opis-projektu)
2. [Architektura](#architektura)
3. [Struktura katalogów](#struktura-katalogów)
4. [Wymagania wstępne](#wymagania-wstępne)
5. [Instalacja lokalna](#instalacja-lokalna)
6. [Uruchomienie przez Docker](#uruchomienie-przez-docker)
7. [Testy jednostkowe](#testy-jednostkowe)
8. [Podręcznik użytkownika](#podręcznik-użytkownika)
9. [Dokumentacja techniczna](#dokumentacja-techniczna)

---

## Opis projektu

Aplikacja rozwiązuje dwa realne problemy analityki piłkarskiej:

1. **Analiza wideo (AI):** automatyczna detekcja zawodników i piłki, śledzenie ruchu, przypisanie drużyn po kolorze koszulki, obliczanie prędkości i dystansu na boisku.
2. **Statystyki meczowe (Web):** pobieranie danych z Flashscore, interaktywna prezentacja wyników, xG, strzałów, podań i innych metryk w przejrzystym dashboardzie.

Integracja obu warstw odbywa się przez pliki w katalogu `data/` (JSON/CSV ze scrapera, MP4 + PKL z pipeline’u CV).

---

## Architektura

Projekt stosuje podział warstwowy inspirowany wzorcem **MVC** oraz zasadami **SOLID** i **DRY**:

```
┌─────────────────────────────────────────────────────────────┐
│  WARSTWA PREZENTACJI (View + Controller)                    │
│  src/dashboard/                                             │
│    app.py          — punkt wejścia Shiny                    │
│    ui_layout.py    — widok (layout UI)                      │
│    server_logic.py — kontroler (reaktywna logika Shiny)     │
│    components.py   — komponenty UI (paski statystyk, kafelki)│
└───────────────────────────┬─────────────────────────────────┘
                            │ wywołania API
┌───────────────────────────▼─────────────────────────────────┐
│  WARSTWA LOGIKI BIZNESOWEJ (Model / Services)               │
│  src/services/                                              │
│    match_data_service.py    — wczytywanie danych meczowych  │
│    tracking_stats_service.py — agregacja dystansu z .pkl    │
│    stats_formatters.py      — formatowanie liczb/statystyk  │
│  src/config/paths.py        — centralna konfiguracja ścieżek│
└───────────────────────────┬─────────────────────────────────┘
                            │ pliki / import modułów CV
┌───────────────────────────▼─────────────────────────────────┐
│  WARSTWA SILNIKA AI (Engine)                                │
│  src/engine/          — fasada integracyjna                 │
│  tracking/            — YOLO + ByteTrack                      │
│  team_assigner/       — K-Means, przypisanie drużyn         │
│  view_transformer/    — homografia boiska                   │
│  speed_and_distance_estimator/ — prędkość i dystans         │
│  camera_movement_estimator/    — korekta ruchu kamery       │
│  player_ball_assigner/         — posiadanie piłki           │
│  main_process.py      — orchestrator pipeline’u CV            │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  WARSTWA DANYCH ZEWNĘTRZNYCH                                │
│  src/scraper/         — FlashScoreScraper (Selenium)        │
│  data/output/         — JSON, CSV, MP4                      │
│  data/stubs/          — pliki pickle z trackingiem           │
└─────────────────────────────────────────────────────────────┘
```

| Zasada | Zastosowanie w projekcie |
|--------|--------------------------|
| **S** (Single Responsibility) | Każdy moduł ma jedną odpowiedzialność: scraper ≠ dashboard ≠ tracker |
| **O** (Open/Closed) | Serwisy można rozszerzać bez modyfikacji UI |
| **D** (Dependency Inversion) | Dashboard zależy od abstrakcji serwisów, nie od szczegółów pickle |
| **DRY** | Wspólna funkcja `build_match_label`, centralne ścieżki w `paths.py` |
| **POLA** | Preferowane proste funkcje i klasy zamiast nadmiernej abstrakcji |

---

## Struktura katalogów

```
FootballAnalysis/
├── main_process.py              # Pipeline analizy wideo (entry point CV)
├── Dockerfile                   # Konteneryzacja dashboardu
├── requirements.txt             # Zależności Python
├── README.md                    # Ten plik
│
├── src/
│   ├── config/                  # Ścieżki i stałe konfiguracyjne
│   ├── services/                # Logika biznesowa (bez UI)
│   ├── engine/                  # Fasada modułów CV
│   ├── dashboard/               # Aplikacja Shiny (UI + controller)
│   └── scraper/                 # Scraper Flashscore
│
├── tracking/                    # Detekcja i śledzenie YOLO
├── team_assigner/               # Przypisanie drużyn (K-Means)
├── view_transformer/            # Transformacja perspektywy
├── speed_and_distance_estimator/
├── camera_movement_estimator/
├── player_ball_assigner/
├── utils/                       # Funkcje geometryczne
│
├── tests/                       # Testy jednostkowe (pytest)
│   ├── test_engine_modules.py
│   ├── test_services.py
│   └── test_tracking_stats_service.py
│
├── data/
│   ├── input_videos/            # Surowe nagrania wejściowe
│   ├── output/                  # Wyniki: MP4, JSON, CSV
│   └── stubs/                   # Cache trackingu (*.pkl)
│
└── models/                      # Wagi YOLO (*.pt)
```

---

## Wymagania wstępne

| Narzędzie | Wersja |
|-----------|--------|
| Python | 3.9+ (zalecane 3.11) |
| Git | dowolna aktualna |
| Docker | opcjonalnie, do wdrożenia kontenerowego |
| Google Chrome | wymagany dla scrapera Flashscore (lokalnie) |

---

## Instalacja lokalna

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/Piciooo2k04/football-video-analytics
cd FootballAnalysis
```

### 2. Środowisko wirtualne i zależności

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Przygotowanie danych

```bash
mkdir -p data/input_videos data/output data/stubs models
```

- Umieść nagranie w `data/input_videos/` (np. `video_2.mp4`)
- Umieść model YOLO w `models/yolov8_football_entities_v1.pt`

### 4. Uruchomienie pipeline’u AI (analiza wideo)

```bash
python main_process.py
```

**Wyniki:**
- `data/output/output_video_2.mp4` — wideo z adnotacjami
- `data/stubs/video_2_processed.pkl` — dane trackingu (dystans, team_id)

### 5. Uruchomienie dashboardu

```bash
shiny run --host 127.0.0.1 --port 8000 src/dashboard/app.py
```

Otwórz w przeglądarce: **http://127.0.0.1:8000**

---

## Uruchomienie przez Docker

### Budowa obrazu

```bash
docker build -t football-analysis-app .
```

### Uruchomienie kontenera

```bash
docker run -p 8000:8000 ^
  -v "%cd%/data:/app/data" ^
  -v "%cd%/models:/app/models" ^
  football-analysis-app
```

*(Na Linuxie/macOS zamień `-v` na odpowiednią ścieżkę, np. `-v $(pwd)/data:/app/data`)*

Dashboard dostępny pod: **http://localhost:8000**

> **Uwaga:** Wolumeny `-v` montują lokalne dane i model YOLO do kontenera. Bez nich dashboard uruchomi się, ale nie będzie miał wideo ani statystyk.

---

## Testy jednostkowe

Testy pokrywają kluczową logikę biznesową (geometria, przypisanie piłki, drużyn, agregacja dystansu, parsowanie danych meczowych).

```bash
pytest tests/ -v
```

Oczekiwany wynik: wszystkie testy **PASSED**.

| Plik testowy | Zakres |
|--------------|--------|
| `test_engine_modules.py` | `bbox_utils`, `PlayerBallAssigner`, `TeamAssigner`, `ViewTransformer` |
| `test_services.py` | `match_data_service`, `stats_formatters` |
| `test_tracking_stats_service.py` | agregacja dystansu, kolory drużyn, ładowanie `.pkl` |

---

## Podręcznik użytkownika

### Zakładka 1: Statystyki po meczowe

#### Krok 1 — Pobranie danych z Flashscore

1. Otwórz dashboard w przeglądarce.
2. W panelu bocznym wklej link do meczu z Flashscore w pole **„Wklej link z Flashscore”**.
3. Kliknij zielony przycisk **„Pobierz dane”**.
4. Poczekaj na powiadomienie *„Dane pobrane i zapisane”*.

#### Krok 2 — Wybór meczu

1. Z listy rozwijanej **„Wybierz spotkanie”** wybierz interesujące spotkanie.
2. Jeśli lista jest pusta, kliknij **„Odśwież dane z pliku”**.

#### Krok 3 — Interpretacja wyników

| Element UI | Znaczenie |
|------------|-----------|
| **Nagłówek** (liga \| kolejka) | Metadane wybranego meczu |
| **Kafelki Gospodarze / Goście** | Nazwy drużyn i wynik końcowy |
| **Kursy 1 / X / 2** | Najlepsze kursy bukmacherskie przedmeczowe |
| **Wykres radarowy** | Porównanie potencjału: strzały, strzały celne, rzuty rożne, wielkie szanse |
| **Zakładki statystyk** (Główne / Atak / Podania / Obrona) | Paski porównawcze niebieski (gospodarze) vs czerwony (goście) |

#### Krok 4 — Odświeżanie danych

- **„Odśwież dane z pliku”** — ponownie wczytuje pliki JSON/CSV z `data/output/` bez ponownego scrapowania.

---

### Zakładka 2: Analiza AI (Wideo)

#### Krok 1 — Przygotowanie wideo

Upewnij się, że uruchomiłeś `python main_process.py` i w `data/output/` znajduje się plik `output_*.mp4`.

#### Krok 2 — Odtwarzanie

1. Przejdź do zakładki **„Analiza AI (Wideo)”**.
2. Z listy **„Wybierz nagranie”** wybierz przetworzone wideo.
3. Odtwarzacz pokaże nagranie z:
   - kolorowymi elipsami pod zawodnikami (kolor = drużyna),
   - numerami ID trackingu,
   - prędkością i dystansem przy zawodnikach,
   - wskaźnikiem posiadania piłki.

#### Krok 3 — Statystyki dystansu

Panel **„Statystyki Dystansu”** wyświetla:

| Element | Znaczenie |
|---------|-----------|
| **Team 1 / Team 2** | Suma dystansów wszystkich zawodników danej drużyny (w metrach, zaokrąglona) |
| **Kolor tła kafelka** | Odpowiada kolorowi koszulki drużyny na wideo |
| **Źródło: plik.pkl** | Nazwa pliku trackingu użytego do obliczeń |

Jeśli widzisz komunikat o braku danych — uruchom ponownie `main_process.py`.

---

## Dokumentacja techniczna

### Technologie

| Obszar | Biblioteki |
|--------|------------|
| Computer Vision | Ultralytics YOLOv8, OpenCV, supervision, ByteTrack |
| Analiza drużyn | scikit-learn (K-Means) |
| Dashboard | Shiny for Python, Plotly, Pandas |
| Scraping | Selenium, BeautifulSoup, webdriver-manager |
| Testy | pytest |
| Wdrożenie | Docker |

### Pipeline CV (`main_process.py`)

1. Wczytanie klatek wideo
2. Detekcja i śledzenie obiektów (YOLO + ByteTrack)
3. Korekta pozycji względem ruchu kamery (optical flow)
4. Transformacja perspektywy na współrzędne boiska (homografia)
5. Obliczenie prędkości i dystansu
6. Przypisanie drużyn (K-Means na kolorach koszulek, odporność na bramkarza)
7. Przypisanie piłki do zawodnika
8. Renderowanie adnotacji i zapis MP4 + PKL

### Format pliku `.pkl`

```python
tracks = {
    "players": [  # lista klatek
        {
            player_id: {
                "bbox": [x1, y1, x2, y2],
                "position": (x, y),
                "position_transformed": (x_m, y_m),
                "speed": float,       # km/h
                "distance": float,    # metry (skumulowane)
                "team_id": 1 | 2 | 0,
                "team_color": (B, G, R),
                "has_ball": bool,
            }
        }
    ],
    "referees": [...],
    "ball": [...],
}
```

### Scrapowanie Flashscore

Scraper zapisuje wyniki do:
- `data/output/flashscore_results.json`
- `data/output/flashscore_results.csv`

Dashboard automatycznie skanuje te pliki przy starcie i po kliknięciu „Odśwież”.

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| Pusta lista meczów | Uruchom scraper lub umieść JSON/CSV w `data/output/` |
| Brak wideo w selektorze | Uruchom `main_process.py`, sprawdź `data/output/*.mp4` |
| Brak statystyk dystansu | Sprawdź `data/stubs/*_processed.pkl`, uruchom pipeline ponownie |
| Błąd scrapera | Zainstaluj Chrome; sprawdź połączenie z internetem |
| Testy nie przechodzą | `pip install -r requirements.txt`, uruchom z katalogu głównego projektu |

---

## Licencja i autorzy

Projekt realizowany w ramach zajęć z Języków Skryptowych na Politechnice Wrocławskiej.

- **Piotr Zakrzewski**
- **Szymon Marczuk**
