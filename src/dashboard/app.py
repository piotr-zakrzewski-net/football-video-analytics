import sys
from pathlib import Path

# Shiny uruchamia app.py z src/dashboard — dodaj katalog główny projektu do sys.path,
# żeby importy typu `from src.scraper import ...` w server_logic działały.
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shiny import App
from ui_layout import app_ui
from server_logic import server

output_video_dir = project_root / "data" / "output"

app = App(app_ui, server, static_assets={"/wideo": output_video_dir})

if not output_video_dir.exists():
    print(f"UWAGA: Folder z wideo nie istnieje: {output_video_dir}")
