from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_VIDEOS_DIR = DATA_DIR / "input_videos"
OUTPUT_DIR = DATA_DIR / "output"
STUBS_DIR = DATA_DIR / "stubs"
MODELS_DIR = PROJECT_ROOT / "models"

MATCH_CSV_PATH = OUTPUT_DIR / "flashscore_results.csv"
MATCH_JSON_PATH = OUTPUT_DIR / "flashscore_results.json"
MATCH_INCREMENTAL_JSON_PATH = OUTPUT_DIR / "flashscore_incremental.json"

PLACEHOLDER_MATCH = "Wczytaj dane..."
