"""Main application window — View."""

import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from ..config import KEYS_DIR, OUT_DIR
from ..logger import Logger
from ..models.connection_state import CONN
from ..theme import (
    ACCENT, BG, BG_CARD, BG_PANEL, BORDER, FG, FG_DIM, FONT_HDR, FONT_LOG, FONT_UI,
)
from ..widgets import make_button, make_label
from .connection_view import ESPConnectionTab
from .key_view import KeyManagementTab
from .manifest_view import ManifestBuilderTab
from .packager_view import FirmwarePackagerTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ASCON-CRA OTA Server")
        self.geometry("850x860")
        self.minsize(780, 650)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.configure(bg=BG)
        self._apply_theme()

        # Title bar
        title_bar = tk.Frame(self, bg=BG_PANEL, pady=10)
        title_bar.pack(fill="x")
        make_label(title_bar, "  🛡  ASCON-CRA OTA Server",
                   font=("Segoe UI", 14, "bold"), fg=ACCENT, bg=BG_PANEL).pack(side="left")
        make_label(title_bar, "Secure Firmware Update Toolset  ",
                   fg=FG_DIM, bg=BG_PANEL).pack(side="right")

        # Notebook (tabs)
        nb = ttk.Notebook(self, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        # Log area (shared across all tabs)
        log_frame = tk.Frame(self, bg=BG_CARD, pady=8, padx=12)
        log_frame.pack(fill="x", side="bottom")

        log_hdr = tk.Frame(log_frame, bg=BG_CARD)
        log_hdr.pack(fill="x", pady=(0, 4))
        make_label(log_hdr, "📋  Log Output", font=FONT_HDR, bg=BG_CARD).pack(side="left")

        log_text = ScrolledText(log_frame, height=10, state="disabled",
                                bg="#0d1117", fg=FG, font=FONT_LOG,
                                relief="flat", borderwidth=0,
                                insertbackground=ACCENT,
                                highlightthickness=1, highlightbackground=BORDER)
        log_text.pack(fill="x")

        logger = Logger(log_text)
        make_button(log_hdr, "Clear", logger.clear, accent=False).pack(side="right")

        # Add tabs (Connection first)
        tab_conn = ESPConnectionTab(nb, logger)
        tab_keys = KeyManagementTab(nb, logger)
        tab_mani = ManifestBuilderTab(nb, logger)
        tab_pkg  = FirmwarePackagerTab(nb, logger)

        nb.add(tab_conn, text="  🔗  Connection  ")
        nb.add(tab_keys, text="  🔑  Key Management  ")
        nb.add(tab_mani, text="  📄  Manifest Builder  ")
        nb.add(tab_pkg,  text="  📦  Firmware Packager  ")

        # Welcome banner
        logger.section("ASCON-CRA OTA Server Ready")
        logger.info(f"Keys directory:      {KEYS_DIR}")
        logger.info(f"Artifacts directory: {OUT_DIR}")
        logger.info("Select a tab above to begin.")

    def _apply_theme(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Dark.TNotebook",
                        background=BG, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                        background=BG_PANEL, foreground=FG_DIM,
                        padding=(12, 6), font=FONT_UI, borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        style.configure("Vertical.TScrollbar",
                        background=BORDER, troughcolor=BG_CARD,
                        arrowcolor=FG_DIM, bordercolor=BG_CARD)

    def _on_close(self):
        """Clean up connections before exit."""
        CONN.close()
        self.destroy()
