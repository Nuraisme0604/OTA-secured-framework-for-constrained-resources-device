"""Key Management tab — View."""

import threading
import tkinter as tk
from pathlib import Path

from ..config import KEYS_DIR
from ..controllers import key_controller
from ..logger import Logger
from ..theme import BG, FG_DIM, FONT_HDR, FONT_LARGE
from ..widgets import browse_dir, make_button, make_card, make_entry, make_label


class KeyManagementTab(tk.Frame):
    def __init__(self, parent, logger: Logger):
        super().__init__(parent, bg=BG)
        self.logger = logger
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # Header
        hdr = make_card(self, pady=18)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        make_label(hdr, "🔑  Key Management", font=FONT_LARGE).pack()
        make_label(hdr, "Generate and manage cryptographic key pairs",
                   fg=FG_DIM).pack()

        # --- Ed25519 Card ---
        card1 = make_card(self, pady=16, padx=20)
        card1.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        card1.columnconfigure(1, weight=1)

        make_label(card1, "Ed25519 Signing Keys", font=FONT_HDR).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        make_label(card1, "Used to sign manifests — Private key stays on server, "
                   "Public key embedded in device firmware.", fg=FG_DIM,
                   wraplength=580, justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        make_label(card1, "Save to:").grid(row=2, column=0, sticky="w", pady=4)
        self.ed25519_dir = tk.StringVar(value=str(KEYS_DIR))
        make_entry(card1, textvariable=self.ed25519_dir).grid(
            row=2, column=1, sticky="ew", padx=(8, 4))
        make_button(card1, "Browse", lambda: browse_dir(self.ed25519_dir),
                    accent=False).grid(row=2, column=2, padx=(0, 0))

        make_label(card1, "Prefix (filename):").grid(row=3, column=0, sticky="w", pady=4)
        self.ed25519_prefix = tk.StringVar(value="server_ed25519")
        make_entry(card1, textvariable=self.ed25519_prefix, width=24).grid(
            row=3, column=1, sticky="w", padx=8)

        make_button(card1, "⚙  Generate Ed25519 Key Pair",
                    self._gen_ed25519).grid(
            row=4, column=0, columnspan=3, pady=(12, 4), sticky="w")

        self.ed25519_pubkey = tk.StringVar(value="(not generated yet)")
        make_label(card1, "Public Key (hex):").grid(row=5, column=0, sticky="w", pady=(8, 0))
        pub_entry = make_entry(card1, textvariable=self.ed25519_pubkey, width=68)
        pub_entry.grid(row=5, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        pub_entry.config(state="readonly")

        # Separator
        from ..theme import BORDER
        tk.Frame(self, bg=BORDER, height=1).grid(
            row=2, column=0, sticky="ew", padx=20, pady=4)

        # --- X25519 Card ---
        card2 = make_card(self, pady=16, padx=20)
        card2.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        card2.columnconfigure(1, weight=1)

        make_label(card2, "X25519 Key Exchange Keys", font=FONT_HDR).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        make_label(card2, "Used for ECDH key exchange to derive session "
                   "encryption keys.", fg=FG_DIM, wraplength=580, justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        make_label(card2, "Save to:").grid(row=2, column=0, sticky="w", pady=4)
        self.x25519_dir = tk.StringVar(value=str(KEYS_DIR))
        make_entry(card2, textvariable=self.x25519_dir).grid(
            row=2, column=1, sticky="ew", padx=(8, 4))
        make_button(card2, "Browse", lambda: browse_dir(self.x25519_dir),
                    accent=False).grid(row=2, column=2)

        make_label(card2, "Prefix (filename):").grid(row=3, column=0, sticky="w", pady=4)
        self.x25519_prefix = tk.StringVar(value="server_x25519")
        make_entry(card2, textvariable=self.x25519_prefix, width=24).grid(
            row=3, column=1, sticky="w", padx=8)

        make_button(card2, "⚙  Generate X25519 Key Pair",
                    self._gen_x25519).grid(
            row=4, column=0, columnspan=3, pady=(12, 4), sticky="w")

        self.x25519_pubkey = tk.StringVar(value="(not generated yet)")
        make_label(card2, "Public Key (hex):").grid(row=5, column=0, sticky="w", pady=(8, 0))
        pub2 = make_entry(card2, textvariable=self.x25519_pubkey, width=68)
        pub2.grid(row=5, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        pub2.config(state="readonly")

    def _gen_ed25519(self):
        def run():
            try:
                pub_hex = key_controller.generate_ed25519(
                    Path(self.ed25519_dir.get()),
                    self.ed25519_prefix.get(),
                    self.logger,
                )
                self.ed25519_pubkey.set(pub_hex)
            except Exception as ex:
                self.logger.err(f"Ed25519 generation failed: {ex}")
        threading.Thread(target=run, daemon=True).start()

    def _gen_x25519(self):
        def run():
            try:
                pub_hex = key_controller.generate_x25519(
                    Path(self.x25519_dir.get()),
                    self.x25519_prefix.get(),
                    self.logger,
                )
                self.x25519_pubkey.set(pub_hex)
            except Exception as ex:
                self.logger.err(f"X25519 generation failed: {ex}")
        threading.Thread(target=run, daemon=True).start()
