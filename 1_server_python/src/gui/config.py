"""Application paths shared across views."""

from pathlib import Path

# 1_server_python/ root — two levels up from src/gui/config.py
APP_DIR  = Path(__file__).resolve().parent.parent.parent
KEYS_DIR = APP_DIR / "keys"
OUT_DIR  = APP_DIR / "artifacts"

KEYS_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)
