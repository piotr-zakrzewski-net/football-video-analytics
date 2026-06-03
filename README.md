# System Analizy Meczów Piłki Nożnej (Computer Vision & AI)

Kompleksowy system do automatycznej analizy wideo z meczów piłkarskich. Projekt łączy zaawansowane modele widzenia maszynowego (detekcja i śledzenie obiektów, transformacja perspektywy) z interaktywnym, reaktywnym interfejsem użytkownika w przeglądarce.

## Technologie
* **Język:** Python 3.9+
* **Sztuczna Inteligencja & CV:** Ultralytics YOLOv8, OpenCV, scikit-learn (K-Means)
* **Interfejs Użytkownika:** Shiny for Python, Plotly, Pandas
* **Testowanie:** pytest
* **Wdrożenie:** Docker

## Architektura Systemu (SOLID & DRY)
Aby sprostać profesjonalnym standardom inżynierii oprogramowania, projekt został ściśle podzielony na dwie niezależne warstwy:

1. **Warstwa Logiki i AI (`src/engine/`):** Niezależny silnik analityczny. Odpowiada za wczytywanie klatek wideo, przepuszczanie ich przez model YOLO, śledzenie zawodników (ByteTrack), mapowanie kolorów koszulek i wyliczanie dystansu. Wyniki są eksportowane do ustrukturyzowanych plików CSV.
2. **Warstwa Prezentacji (`src/dashboard/`):** Zbudowana w frameworku Shiny. Zajmuje się wyłącznie odczytywaniem wygenerowanych danych i wyświetlaniem interaktywnych statystyk oraz wykresów.

Taki podział zapewnia całkowitą separację logiki od interfejsu (Single Responsibility Principle) i umożliwia niezależne testowanie oraz modyfikację każdego z modułów.

## Wymagania wstępne (Prerequisites)
Przed uruchomieniem upewnij się, że posiadasz zainstalowanego **Pythona 3.9+** oraz narzędzie **Git**. Zalecane jest używanie środowiska wirtualnego.

## Instalacja i Uruchomienie (Lokalnie)

**1. Klonowanie repozytorium i struktura**
```bash
git clone https://github.com/Piciooo2k04/football-video-analytics
cd FootballAnalysis
```

**2. Przygotowanie środowiska**
```bash
python -m venv venv
source venv/Scripts/activate  # (Windows PowerShell: .\venv\Scripts\activate)
pip install -r requirements.txt
```

**3. Uruchomienie analizy wideo (Silnik AI)**
Umieść plik wideo do analizy w katalogu `data/input/` (np. `test_video.mp4`), a następnie uruchom:
```bash
python main_process.py
```
*(Podczas pierwszego uruchomienia skrypt automatycznie pobierze niezbędne wagi modelu YOLO).*

**4. Uruchomienie interfejsu analitycznego (Dashboard)**
Aby włączyć aplikację webową z wynikami, uruchom serwer Shiny:
```bash
shiny run --host 127.0.0.1 --port 8000 src/dashboard/app.py
```
Aplikacja będzie dostępna w przeglądarce pod adresem: `http://127.0.0.1:8000`.

## Wdrożenie (Docker)
Aplikacja jest gotowa do uruchomienia w izolowanym kontenerze Dockerowym, co eliminuje problemy z zależnościami systemowymi.

Budowa obrazu:
```bash
docker build -t football-analysis-app .
```
Uruchomienie kontenera:
```bash
docker run -p 8000:8000 football-analysis-app
```

## Testy Jednostkowe
Kluczowe moduły matematyczne (np. obliczanie dystansu na podstawie transformacji perspektywy) zostały pokryte testami jednostkowymi. Aby je uruchomić, użyj polecenia:
```bash
pytest tests/
```

## Autorzy
Projekt realizowany w ramach zajęć na z Języków Skryptowych na Politechnice Wrocławskiej.
* **Piotr Zakrzewski** 
* **Szymon Marczuk**