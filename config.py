"""Shared application paths and constants."""
from pathlib import Path

APP_NAME = "Aadya Water Buddy"
APP_DIR = Path.home() / "Library" / "Application Support" / "AadyaWaterBuddy"
DATA_FILE = APP_DIR / "water_log.json"
SETTINGS_FILE = APP_DIR / "settings.json"

PROJECT_DIR = Path(__file__).resolve().parent
ASSET_DIR = PROJECT_DIR / "assets"
HAPPY_PATH = ASSET_DIR / "aadya_happy.png"
SAD_PATH = ASSET_DIR / "aadya_sad.png"
DANCE_FRAMES_DIR = ASSET_DIR / "dance_happy"
HAPPY_WALK_DIR = ASSET_DIR / "happy_walk"
SAD_WALK_DIR = ASSET_DIR / "sad_walk"
WALK_FRAMES_DIR = ASSET_DIR / "walk_right"  # backward-compatible fallback
