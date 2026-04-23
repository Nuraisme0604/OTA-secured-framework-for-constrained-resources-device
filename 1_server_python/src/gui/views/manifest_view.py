"""Manifest Builder tab — View."""

import os
import threading
import tkinter as tk
from tkinter import messagebox

from ..config import OUT_DIR
from ..controllers import manifest_controller
from ..logger import Logger
from ..theme import BG, BG_CARD, BORDER, FG_DIM, FONT_HDR, FONT_LARGE
from ..widgets import browse_file, browse_save, make_button, make_card, make_entry, make_label


class ManifestBuilderTab(tk.Frame):
    def __init__(self, parent, logger: Logger):
        super().__init__(parent, bg=BG)
        self.logger = logger
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # Header
        hdr = make_card(self, pady=18)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        make_label(hdr, "📄  Manifest Builder", font=FONT_LARGE).pack()
        make_label(hdr, "Create and sign OTA firmware manifests (hardware passport)",
                   fg=FG_DIM).pack()

        # Input card
        card = make_card(self, pady=16, padx=20)
        card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        card.columnconfigure(1, weight=1)

        row_idx = 0

        # Firmware file
        make_label(card, "Firmware (.bin):").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.fw_path = tk.StringVar()
        make_entry(card, textvariable=self.fw_path).grid(
            row=row_idx, column=1, sticky="ew", padx=(8, 4))
        make_button(card, "Browse", lambda: browse_file(
            self.fw_path, [("Binary files", "*.bin"), ("All files", "*.*")],
            "Select Firmware Binary"), accent=False).grid(row=row_idx, column=2)
        row_idx += 1

        # Private key file
        make_label(card, "Private Key (.pem):").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.key_path = tk.StringVar()
        make_entry(card, textvariable=self.key_path).grid(
            row=row_idx, column=1, sticky="ew", padx=(8, 4))
        make_button(card, "Browse", lambda: browse_file(
            self.key_path, [("PEM files", "*.pem"), ("All files", "*.*")],
            "Select Ed25519 Private Key"), accent=False).grid(row=row_idx, column=2)
        row_idx += 1

        # Output file
        make_label(card, "Output Manifest:").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.out_path = tk.StringVar(value=str(OUT_DIR / "manifest.bin"))
        make_entry(card, textvariable=self.out_path).grid(
            row=row_idx, column=1, sticky="ew", padx=(8, 4))
        make_button(card, "Browse", lambda: browse_save(
            self.out_path, [("Binary files", "*.bin")], ".bin",
            "Save Manifest As"), accent=False).grid(row=row_idx, column=2)
        row_idx += 1

        # Divider
        tk.Frame(card, bg=BORDER, height=1).grid(
            row=row_idx, column=0, columnspan=3, sticky="ew", pady=10)
        row_idx += 1

        make_label(card, "Firmware Information", font=FONT_HDR).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 8))
        row_idx += 1

        # Version major/minor/patch
        make_label(card, "Version:").grid(row=row_idx, column=0, sticky="w", pady=6)
        ver_frame = tk.Frame(card, bg=BG_CARD)
        ver_frame.grid(row=row_idx, column=1, sticky="w", padx=8)
        self.ver_major = tk.StringVar(value="1")
        self.ver_minor = tk.StringVar(value="0")
        self.ver_patch = tk.StringVar(value="0")
        for label_txt, var in [("Major", self.ver_major),
                               ("Minor", self.ver_minor),
                               ("Patch", self.ver_patch)]:
            make_label(ver_frame, f"{label_txt}:", fg=FG_DIM).pack(side="left", padx=(0, 2))
            make_entry(ver_frame, textvariable=var, width=5).pack(side="left", padx=(0, 14))
        row_idx += 1

        # Vendor ID
        make_label(card, "Vendor ID (4 chars):").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.vendor_id = tk.StringVar(value="NCKT")
        make_entry(card, textvariable=self.vendor_id, width=12).grid(
            row=row_idx, column=1, sticky="w", padx=8)
        row_idx += 1

        # Device class
        make_label(card, "Device Class (2 chars):").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.device_class = tk.StringVar(value="F1")
        make_entry(card, textvariable=self.device_class, width=8).grid(
            row=row_idx, column=1, sticky="w", padx=8)
        row_idx += 1

        # Security version
        make_label(card, "Security Version:").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.sec_ver = tk.StringVar(value="1")
        make_entry(card, textvariable=self.sec_ver, width=8).grid(
            row=row_idx, column=1, sticky="w", padx=8)
        row_idx += 1

        # Chunk size
        make_label(card, "Chunk Size (bytes):").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.chunk_size = tk.StringVar(value="1024")
        make_entry(card, textvariable=self.chunk_size, width=10).grid(
            row=row_idx, column=1, sticky="w", padx=8)
        row_idx += 1

        make_button(card, "  🔨  Build & Sign Manifest  ", self._build_manifest).grid(
            row=row_idx, column=0, columnspan=3, pady=(16, 4), sticky="w")

    def _build_manifest(self):
        fw_path = self.fw_path.get().strip()
        key_path = self.key_path.get().strip()
        out_path = self.out_path.get().strip()

        if not fw_path or not os.path.isfile(fw_path):
            messagebox.showerror("Error", "Please select a valid firmware file.")
            return
        if not key_path or not os.path.isfile(key_path):
            messagebox.showerror("Error", "Please select a valid private key file.")
            return

        def run():
            try:
                manifest_controller.build_manifest(
                    fw_path=fw_path,
                    key_path=key_path,
                    out_path=out_path,
                    vendor_id=self.vendor_id.get(),
                    device_class=self.device_class.get(),
                    major=int(self.ver_major.get() or "1"),
                    minor=int(self.ver_minor.get() or "0"),
                    patch=int(self.ver_patch.get() or "0"),
                    security_version=int(self.sec_ver.get() or "1"),
                    chunk_size=int(self.chunk_size.get() or "1024"),
                    logger=self.logger,
                )
            except Exception as ex:
                import traceback
                self.logger.err(f"Build failed: {ex}")
                self.logger.err(traceback.format_exc())

        threading.Thread(target=run, daemon=True).start()
