"""Firmware Packager tab — View."""

import os
import threading
import tkinter as tk
from tkinter import messagebox

from ..config import OUT_DIR
from ..controllers import packager_controller
from ..logger import Logger
from ..theme import BG, BG_CARD, BORDER, FG, FG_DIM, FONT_HDR, FONT_LARGE
from ..widgets import browse_file, browse_save, make_button, make_card, make_entry, make_label


class FirmwarePackagerTab(tk.Frame):
    def __init__(self, parent, logger: Logger):
        super().__init__(parent, bg=BG)
        self.logger = logger
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # Header
        hdr = make_card(self, pady=18)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        make_label(hdr, "📦  Firmware Packager", font=FONT_LARGE).pack()
        make_label(hdr, "Split & encrypt firmware into ASCON-128a secured chunks for OTA",
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

        # Output file
        make_label(card, "Output Package:").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.out_path = tk.StringVar(value=str(OUT_DIR / "firmware.pkg"))
        make_entry(card, textvariable=self.out_path).grid(
            row=row_idx, column=1, sticky="ew", padx=(8, 4))
        make_button(card, "Browse", lambda: browse_save(
            self.out_path, [("Package files", "*.pkg"), ("All files", "*.*")], ".pkg",
            "Save Package As"), accent=False).grid(row=row_idx, column=2)
        row_idx += 1

        # Divider
        tk.Frame(card, bg=BORDER, height=1).grid(
            row=row_idx, column=0, columnspan=3, sticky="ew", pady=10)
        row_idx += 1

        make_label(card, "Encryption Settings", font=FONT_HDR).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 8))
        row_idx += 1

        # Chunk size
        make_label(card, "Chunk Size (bytes):").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.chunk_size = tk.StringVar(value="1024")
        make_entry(card, textvariable=self.chunk_size, width=10).grid(
            row=row_idx, column=1, sticky="w", padx=8)
        make_label(card, "(default 1024 — must match manifest)", fg=FG_DIM).grid(
            row=row_idx, column=2, sticky="w", padx=8)
        row_idx += 1

        # Key mode
        make_label(card, "Encryption Key:").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.key_mode = tk.StringVar(value="random")
        key_frame = tk.Frame(card, bg=BG_CARD)
        key_frame.grid(row=row_idx, column=1, columnspan=2, sticky="w", padx=8)
        tk.Radiobutton(key_frame, text="Generate random key (for testing)",
                       variable=self.key_mode, value="random",
                       bg=BG_CARD, fg=FG, selectcolor=BG,
                       activebackground=BG_CARD,
                       command=self._toggle_key_mode).pack(side="left", padx=(0, 16))
        tk.Radiobutton(key_frame, text="Use hex key:",
                       variable=self.key_mode, value="hex",
                       bg=BG_CARD, fg=FG, selectcolor=BG,
                       activebackground=BG_CARD,
                       command=self._toggle_key_mode).pack(side="left")
        row_idx += 1

        self.manual_key = tk.StringVar()
        self.key_entry = make_entry(card, textvariable=self.manual_key, width=40)
        self.key_entry.grid(row=row_idx, column=1, sticky="w", padx=8)
        self.key_entry.config(state="disabled")
        make_label(card, "(32 hex chars = 16 bytes)", fg=FG_DIM).grid(
            row=row_idx, column=2, sticky="w", padx=8)
        row_idx += 1

        # UART baudrate
        make_label(card, "UART Baudrate:").grid(row=row_idx, column=0, sticky="w", pady=6)
        self.baudrate = tk.StringVar(value="115200")
        baud_frame = tk.Frame(card, bg=BG_CARD)
        baud_frame.grid(row=row_idx, column=1, sticky="w", padx=8)
        for baud in ["9600", "57600", "115200", "230400"]:
            tk.Radiobutton(baud_frame, text=baud, variable=self.baudrate, value=baud,
                           bg=BG_CARD, fg=FG, selectcolor=BG,
                           activebackground=BG_CARD).pack(side="left", padx=4)
        row_idx += 1

        # Buttons row
        btn_frame = tk.Frame(card, bg=BG_CARD)
        btn_frame.grid(row=row_idx, column=0, columnspan=3, pady=(16, 4), sticky="w")
        make_button(btn_frame, "  📦  Package Firmware  ", self._package).pack(
            side="left", padx=(0, 8))
        make_button(btn_frame, "  ⏱  Estimate Transfer Time  ",
                    self._estimate_time, accent=False).pack(side="left")

        # Generated key display
        row_idx += 1
        make_label(card, "Encryption Key Used:").grid(row=row_idx, column=0, sticky="w", pady=(8, 4))
        self.used_key_var = tk.StringVar(value="(will be shown after packaging)")
        used_key_entry = make_entry(card, textvariable=self.used_key_var, width=68)
        used_key_entry.grid(row=row_idx, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        used_key_entry.config(state="readonly")

    def _toggle_key_mode(self):
        if self.key_mode.get() == "hex":
            self.key_entry.config(state="normal")
        else:
            self.key_entry.config(state="disabled")

    def _package(self):
        fw_path = self.fw_path.get().strip()
        out_path = self.out_path.get().strip()

        if not fw_path or not os.path.isfile(fw_path):
            messagebox.showerror("Error", "Please select a valid firmware file.")
            return

        def run():
            try:
                key = packager_controller.resolve_key(
                    self.key_mode.get(), self.manual_key.get())
                self.used_key_var.set(key.hex())

                packager_controller.package_firmware(
                    fw_path=fw_path,
                    out_path=out_path,
                    key=key,
                    chunk_size=int(self.chunk_size.get() or "1024"),
                    baudrate=int(self.baudrate.get()),
                    logger=self.logger,
                )
            except Exception as ex:
                import traceback
                self.logger.err(f"Packaging failed: {ex}")
                self.logger.err(traceback.format_exc())

        threading.Thread(target=run, daemon=True).start()

    def _estimate_time(self):
        fw_path = self.fw_path.get().strip()
        if not fw_path or not os.path.isfile(fw_path):
            messagebox.showerror("Error", "Please select a valid firmware file first.")
            return

        def run():
            try:
                packager_controller.estimate_transfer(
                    fw_path=fw_path,
                    chunk_size=int(self.chunk_size.get() or "1024"),
                    selected_baud=int(self.baudrate.get()),
                    logger=self.logger,
                )
            except Exception as ex:
                self.logger.err(f"Estimation failed: {ex}")

        threading.Thread(target=run, daemon=True).start()
