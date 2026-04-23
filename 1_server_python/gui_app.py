"""
gui_app.py - ASCON-CRA OTA Server GUI (entry point)

Thin entry point. The actual UI is organized under src/gui/ following MVC:
  src/gui/theme.py, widgets.py, logger.py, config.py
  src/gui/models/       — shared state (ConnectionState)
  src/gui/controllers/  — key / manifest / packager / connection logic
  src/gui/views/        — Tkinter tabs + main App window
"""

import sys
from pathlib import Path

# Add src/ to sys.path so the flat domain modules (crypto_utils, manifest_builder,
# packet_builder) and the gui package are both importable.
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

from gui.views.app_view import App  # noqa: E402


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
