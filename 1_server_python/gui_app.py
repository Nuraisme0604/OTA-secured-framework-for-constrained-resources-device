"""
gui_app.py - ASCON-CRA OTA Server GUI

A Tkinter-based graphical interface for the OTA firmware packaging toolset.
Provides Key Management, Manifest Building, and Firmware Packaging in one app.
"""

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from datetime import datetime

# --- Add src to path so we can import server modules ---
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

# --- Default key and artifact directories ---
APP_DIR   = Path(__file__).parent
KEYS_DIR  = APP_DIR / "keys"
OUT_DIR   = APP_DIR / "artifacts"
KEYS_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)


# =============================================================================
# Color Palette & Theme
# =============================================================================

BG         = "#1a1a2e"   # Dark navy background
BG_CARD    = "#16213e"   # Slightly lighter card background
BG_PANEL   = "#0f3460"   # Accent panel background
ACCENT     = "#00bfa5"   # Teal accent
ACCENT_DIM = "#007a6e"   # Dimmed teal for hover
FG         = "#e0e0e0"   # Main text
FG_DIM     = "#9e9e9e"   # Secondary text
FG_LOG_OK  = "#69f0ae"   # Log success color (green)
FG_LOG_ERR = "#ff5252"   # Log error color (red)
FG_LOG_INF = "#40c4ff"   # Log info color (blue)
FG_LOG_WRN = "#ffd740"   # Log warning color (yellow)
BORDER     = "#263859"   # Border color
FONT_UI    = ("Segoe UI", 10)
FONT_HDR   = ("Segoe UI", 12, "bold")
FONT_LOG   = ("Consolas", 9)
FONT_MONO  = ("Consolas", 10)
FONT_LARGE = ("Segoe UI", 14, "bold")


# =============================================================================
# Logger Widget
# =============================================================================

class Logger:
    """Writes tagged messages to a ScrolledText widget."""

    def __init__(self, widget: ScrolledText):
        self.widget = widget
        self.widget.tag_config("OK",  foreground=FG_LOG_OK)
        self.widget.tag_config("ERR", foreground=FG_LOG_ERR)
        self.widget.tag_config("INF", foreground=FG_LOG_INF)
        self.widget.tag_config("WRN", foreground=FG_LOG_WRN)
        self.widget.tag_config("DIM", foreground=FG_DIM)
        self.widget.tag_config("NRM", foreground=FG)

    def _write(self, level: str, msg: str, tag: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.widget.config(state="normal")
        self.widget.insert("end", f"[{ts}] ", "DIM")
        self.widget.insert("end", f"[{level}] ", tag)
        self.widget.insert("end", f"{msg}\n", "NRM")
        self.widget.config(state="disabled")
        self.widget.see("end")

    def ok(self, msg):  self._write("OK ", msg, "OK")
    def err(self, msg): self._write("ERR", msg, "ERR")
    def info(self, msg):self._write("INF", msg, "INF")
    def warn(self, msg):self._write("WRN", msg, "WRN")

    def section(self, title: str):
        border = "─" * 50
        self.widget.config(state="normal")
        self.widget.insert("end", f"\n{border}\n  {title}\n{border}\n", "INF")
        self.widget.config(state="disabled")
        self.widget.see("end")

    def clear(self):
        self.widget.config(state="normal")
        self.widget.delete("1.0", "end")
        self.widget.config(state="disabled")


# =============================================================================
# Reusable UI Helpers
# =============================================================================

def make_card(parent, **kwargs) -> tk.Frame:
    return tk.Frame(parent, bg=BG_CARD, relief="flat",
                    highlightthickness=1, highlightbackground=BORDER, **kwargs)


def make_label(parent, text, font=FONT_UI, fg=FG, bg=None, **kwargs) -> tk.Label:
    actual_bg = bg if bg is not None else parent["bg"]
    return tk.Label(parent, text=text, bg=actual_bg, fg=fg, font=font, **kwargs)



def make_entry(parent, textvariable=None, width=40, **kwargs) -> tk.Entry:
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    bg="#0d1b2a", fg=FG, insertbackground=ACCENT,
                    relief="flat", highlightthickness=1,
                    highlightbackground=BORDER, highlightcolor=ACCENT,
                    font=FONT_MONO, **kwargs)


def make_button(parent, text, command, accent=True, **kwargs) -> tk.Button:
    bg = ACCENT if accent else BG_PANEL
    hover_bg = ACCENT_DIM if accent else "#1a3a6e"
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg="#ffffff" if accent else FG,
                    activebackground=hover_bg, activeforeground="#ffffff",
                    relief="flat", cursor="hand2", font=FONT_UI,
                    padx=14, pady=6, **kwargs)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def browse_file(var: tk.StringVar, filetypes: list, title="Select File"):
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    if path:
        var.set(path)


def browse_save(var: tk.StringVar, filetypes: list, default_ext: str, title="Save As"):
    path = filedialog.asksaveasfilename(title=title, filetypes=filetypes,
                                        defaultextension=default_ext)
    if path:
        var.set(path)


# =============================================================================
# Tab 1: Key Management
# =============================================================================

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
        make_button(card1, "Browse", lambda: self._browse_dir(self.ed25519_dir),
                    accent=False).grid(row=2, column=2, padx=(0, 0))

        make_label(card1, "Prefix (filename):").grid(row=3, column=0, sticky="w", pady=4)
        self.ed25519_prefix = tk.StringVar(value="server_ed25519")
        make_entry(card1, textvariable=self.ed25519_prefix, width=24).grid(
            row=3, column=1, sticky="w", padx=8)

        btn_ed = make_button(card1, "⚙  Generate Ed25519 Key Pair",
                             self._gen_ed25519)
        btn_ed.grid(row=4, column=0, columnspan=3, pady=(12, 4), sticky="w")

        # Public key display
        self.ed25519_pubkey = tk.StringVar(value="(not generated yet)")
        make_label(card1, "Public Key (hex):").grid(row=5, column=0, sticky="w", pady=(8, 0))
        pub_entry = make_entry(card1, textvariable=self.ed25519_pubkey, width=68)
        pub_entry.grid(row=5, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        pub_entry.config(state="readonly")

        # Separator
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.grid(row=2, column=0, sticky="ew", padx=20, pady=4)

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
        make_button(card2, "Browse", lambda: self._browse_dir(self.x25519_dir),
                    accent=False).grid(row=2, column=2)

        make_label(card2, "Prefix (filename):").grid(row=3, column=0, sticky="w", pady=4)
        self.x25519_prefix = tk.StringVar(value="server_x25519")
        make_entry(card2, textvariable=self.x25519_prefix, width=24).grid(
            row=3, column=1, sticky="w", padx=8)

        btn_xk = make_button(card2, "⚙  Generate X25519 Key Pair",
                             self._gen_x25519)
        btn_xk.grid(row=4, column=0, columnspan=3, pady=(12, 4), sticky="w")

        self.x25519_pubkey = tk.StringVar(value="(not generated yet)")
        make_label(card2, "Public Key (hex):").grid(row=5, column=0, sticky="w", pady=(8, 0))
        pub2 = make_entry(card2, textvariable=self.x25519_pubkey, width=68)
        pub2.grid(row=5, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        pub2.config(state="readonly")

    def _browse_dir(self, var: tk.StringVar):
        d = filedialog.askdirectory(title="Select Output Directory")
        if d:
            var.set(d)

    def _gen_ed25519(self):
        def run():
            try:
                from crypto_utils import ed25519_generate_keypair
                from cryptography.hazmat.primitives.asymmetric import ed25519 as ed
                from cryptography.hazmat.primitives import serialization

                self.logger.section("Generate Ed25519 Key Pair")
                kp = ed25519_generate_keypair()
                dest = Path(self.ed25519_dir.get())
                prefix = self.ed25519_prefix.get().strip() or "server_ed25519"

                # Save private key as PEM
                priv_pem_path = dest / f"{prefix}_private.pem"
                priv_key_obj = ed.Ed25519PrivateKey.from_private_bytes(kp.private_key)
                pem_bytes = priv_key_obj.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption()
                )
                priv_pem_path.write_bytes(pem_bytes)

                # Save public key as raw bytes
                pub_path = dest / f"{prefix}_public.bin"
                pub_path.write_bytes(kp.public_key)

                # Also save as hex text
                pub_hex_path = dest / f"{prefix}_public.hex"
                pub_hex_path.write_text(kp.public_key.hex())

                self.ed25519_pubkey.set(kp.public_key.hex())
                self.logger.ok(f"Private key (PEM) → {priv_pem_path}")
                self.logger.ok(f"Public key (bin)  → {pub_path}")
                self.logger.ok(f"Public key (hex)  → {pub_hex_path}")
                self.logger.info(f"Public key: {kp.public_key.hex()}")
            except Exception as ex:
                self.logger.err(f"Ed25519 generation failed: {ex}")
        threading.Thread(target=run, daemon=True).start()

    def _gen_x25519(self):
        def run():
            try:
                from crypto_utils import x25519_generate_keypair
                from cryptography.hazmat.primitives.asymmetric import x25519
                from cryptography.hazmat.primitives import serialization

                self.logger.section("Generate X25519 Key Pair")
                kp = x25519_generate_keypair()
                dest = Path(self.x25519_dir.get())
                prefix = self.x25519_prefix.get().strip() or "server_x25519"

                # Save private key raw
                priv_path = dest / f"{prefix}_private.bin"
                priv_path.write_bytes(kp.private_key)

                # Save public key raw + hex
                pub_path = dest / f"{prefix}_public.bin"
                pub_path.write_bytes(kp.public_key)
                pub_hex_path = dest / f"{prefix}_public.hex"
                pub_hex_path.write_text(kp.public_key.hex())

                self.x25519_pubkey.set(kp.public_key.hex())
                self.logger.ok(f"Private key (bin) → {priv_path}")
                self.logger.ok(f"Public key (bin)  → {pub_path}")
                self.logger.ok(f"Public key (hex)  → {pub_hex_path}")
                self.logger.info(f"Public key: {kp.public_key.hex()}")
            except Exception as ex:
                self.logger.err(f"X25519 generation failed: {ex}")
        threading.Thread(target=run, daemon=True).start()


# =============================================================================
# Tab 2: Manifest Builder
# =============================================================================

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

        # Firmware Info sub-section
        make_label(card, "Firmware Information", font=FONT_HDR).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 8))
        row_idx += 1

        # Version fields (major / minor / patch) on one row
        make_label(card, "Version:").grid(row=row_idx, column=0, sticky="w", pady=6)
        ver_frame = tk.Frame(card, bg=BG_CARD)
        ver_frame.grid(row=row_idx, column=1, sticky="w", padx=8)
        self.ver_major = tk.StringVar(value="1")
        self.ver_minor = tk.StringVar(value="0")
        self.ver_patch = tk.StringVar(value="0")
        for label_txt, var in [("Major", self.ver_major), ("Minor", self.ver_minor), ("Patch", self.ver_patch)]:
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

        # Build button
        btn = make_button(card, "  🔨  Build & Sign Manifest  ", self._build_manifest)
        btn.grid(row=row_idx, column=0, columnspan=3, pady=(16, 4), sticky="w")

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
                from manifest_builder import ManifestConfig, ManifestBuilder, pack_version

                self.logger.section("Build Manifest")

                vendor = self.vendor_id.get().strip()[:4].ljust(4, '\x00').encode()
                dev_cls = self.device_class.get().strip()[:2].ljust(2, '\x00').encode()
                fw_ver = pack_version(
                    int(self.ver_major.get() or "1"),
                    int(self.ver_minor.get() or "0"),
                    int(self.ver_patch.get() or "0")
                )
                sec_ver = int(self.sec_ver.get() or "1")
                chunk_sz = int(self.chunk_size.get() or "1024")

                self.logger.info(f"Firmware:         {fw_path}")
                self.logger.info(f"Private key:      {key_path}")
                self.logger.info(f"Version:          {self.ver_major.get()}.{self.ver_minor.get()}.{self.ver_patch.get()}")
                self.logger.info(f"Vendor/DevClass:  {self.vendor_id.get()} / {self.device_class.get()}")
                self.logger.info(f"Security version: {sec_ver}")
                self.logger.info(f"Chunk size:       {chunk_sz} bytes")

                config = ManifestConfig(
                    vendor_id=vendor,
                    device_class=dev_cls,
                    device_id=0,
                    fw_version=fw_ver,
                    security_version=sec_ver,
                    chunk_size=chunk_sz,
                )

                builder = ManifestBuilder(config, key_path)
                manifest = builder.build_from_file(fw_path)
                builder.save_manifest(manifest, out_path)

                info = ManifestBuilder.parse_manifest(manifest)
                self.logger.ok(f"Manifest saved → {out_path}")
                self.logger.ok(f"Manifest size:  {len(manifest)} bytes")
                self.logger.info("──── Manifest Fields ────")
                for k, v in info.items():
                    self.logger.info(f"  {k:<20} = {v}")

            except Exception as ex:
                import traceback
                self.logger.err(f"Build failed: {ex}")
                self.logger.err(traceback.format_exc())

        threading.Thread(target=run, daemon=True).start()


# =============================================================================
# Tab 3: Firmware Packager
# =============================================================================

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

        # UART baudrate (for time estimate)
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

    def _get_key(self) -> bytes:
        from crypto_utils import generate_random_bytes
        if self.key_mode.get() == "hex":
            hex_str = self.manual_key.get().strip().replace(" ", "")
            if len(hex_str) != 32:
                raise ValueError("Hex key must be exactly 32 hex characters (16 bytes)")
            return bytes.fromhex(hex_str)
        else:
            return generate_random_bytes(16)

    def _package(self):
        fw_path = self.fw_path.get().strip()
        out_path = self.out_path.get().strip()

        if not fw_path or not os.path.isfile(fw_path):
            messagebox.showerror("Error", "Please select a valid firmware file.")
            return

        def run():
            try:
                from packet_builder import PacketBuilder
                from crypto_utils import generate_random_bytes

                self.logger.section("Package Firmware")

                key = self._get_key()
                nonce_base = generate_random_bytes(16)
                chunk_sz = int(self.chunk_size.get() or "1024")

                self.logger.info(f"Firmware:    {fw_path}")
                self.logger.info(f"Output:      {out_path}")
                self.logger.info(f"Chunk size:  {chunk_sz} bytes")
                self.logger.info(f"Key (hex):   {key.hex()}")
                self.logger.info(f"Nonce base:  {nonce_base.hex()}")

                # Update the key display entry
                self.used_key_var.set(key.hex())

                builder = PacketBuilder(chunk_size=chunk_sz)
                total_chunks, total_bytes = builder.package_firmware(
                    fw_path, key, nonce_base, out_path)

                fw_size = os.path.getsize(fw_path)
                from packet_builder import calculate_transfer_time
                baud = int(self.baudrate.get())
                est_time = calculate_transfer_time(fw_size, chunk_sz, baud)

                self.logger.ok(f"Package saved → {out_path}")
                self.logger.ok(f"Total chunks:  {total_chunks}")
                self.logger.ok(f"Encrypted bytes: {total_bytes:,}")
                self.logger.info(f"Estimated transfer @ {baud} baud: {est_time:.2f}s")
                self.logger.warn("⚠  Save the Key (hex) above — it's required by the "
                                 "device to decrypt the firmware!")

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
                from packet_builder import calculate_transfer_time
                fw_size = os.path.getsize(fw_path)
                chunk_sz = int(self.chunk_size.get() or "1024")
                baud = int(self.baudrate.get())

                self.logger.section("Transfer Time Estimate")
                self.logger.info(f"Firmware size: {fw_size:,} bytes ({fw_size/1024:.1f} KB)")
                self.logger.info(f"Chunk size:    {chunk_sz} bytes")
                chunks = (fw_size + chunk_sz - 1) // chunk_sz
                self.logger.info(f"Total chunks:  {chunks}")

                for baud_rate in [9600, 57600, 115200, 230400]:
                    t = calculate_transfer_time(fw_size, chunk_sz, baud_rate)
                    marker = "  ◀ selected" if baud_rate == baud else ""
                    self.logger.info(f"  @ {baud_rate:>6} baud → {t:6.2f}s{marker}")

            except Exception as ex:
                self.logger.err(f"Estimation failed: {ex}")

        threading.Thread(target=run, daemon=True).start()


# =============================================================================
# Shared Connection State
# =============================================================================

class ConnectionState:
    """Shared connection state accessible by all GUI tabs."""
    def __init__(self):
        self.connected: bool = False
        self.mode: str = ""         # 'wifi' or 'serial'
        self.target: str = ""        # 'ip:port' or 'COM3'
        self.latency_ms: float = 0.0
        self.device_name: str = ""
        self._socket = None          # TCP socket
        self._serial = None          # pyserial Serial

    def close(self):
        """Close any open connection."""
        try:
            if self._socket:
                self._socket.close()
        except Exception:
            pass
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
        except Exception:
            pass
        self._socket = None
        self._serial = None
        self.connected = False


CONN = ConnectionState()


# =============================================================================
# Tab 0: ESP32 Connection Manager
# =============================================================================

class ESPConnectionTab(tk.Frame):
    """Manages the connection between this PC server and the ESP32 Gateway."""

    PING_MSG  = b"PING\r\n"
    PONG_PREFIX = b"PONG"
    AT_CMD    = b"AT\r\n"
    AT_OK     = b"OK"

    def __init__(self, parent, logger: Logger):
        super().__init__(parent, bg=BG)
        self.logger = logger
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # ── Header ────────────────────────────────────────────────────
        hdr = make_card(self, pady=18)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        make_label(hdr, "🔗  ESP32 Connection Manager", font=FONT_LARGE).pack()
        make_label(hdr, "Connect to ESP32 Gateway via WiFi (TCP) or USB Serial",
                   fg=FG_DIM).pack()

        # ── Connection Type ───────────────────────────────────────────
        type_card = make_card(self, padx=20, pady=14)
        type_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 4))

        make_label(type_card, "Connection Type", font=FONT_HDR).grid(
            row=0, column=0, sticky="w", pady=(0, 10))

        self.conn_mode = tk.StringVar(value="wifi")
        mode_frame = tk.Frame(type_card, bg=BG_CARD)
        mode_frame.grid(row=1, column=0, sticky="w")

        for val, label_txt, icon in [("wifi", "WiFi / Network", "🌐"),
                                     ("serial", "USB Serial (UART)", "🔌")]:
            rb = tk.Radiobutton(
                mode_frame, text=f"  {icon}  {label_txt}",
                variable=self.conn_mode, value=val,
                bg=BG_CARD, fg=FG, selectcolor=BG,
                activebackground=BG_CARD, font=FONT_UI,
                command=self._on_mode_change
            )
            rb.pack(side="left", padx=(0, 24))

        # ── WiFi Settings Card ────────────────────────────────────────
        self.wifi_card = make_card(self, padx=20, pady=14)
        self.wifi_card.columnconfigure(1, weight=1)
        self.wifi_card.grid(row=2, column=0, sticky="ew", padx=20, pady=4)

        make_label(self.wifi_card, "🌐  WiFi / Network Settings",
                   font=FONT_HDR).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        make_label(self.wifi_card, "ESP32 IP Address:").grid(
            row=1, column=0, sticky="w", pady=5)
        self.wifi_ip = tk.StringVar(value="192.168.1.100")
        make_entry(self.wifi_card, textvariable=self.wifi_ip, width=22).grid(
            row=1, column=1, sticky="w", padx=8)

        make_label(self.wifi_card, "TCP Port:").grid(
            row=2, column=0, sticky="w", pady=5)
        self.wifi_port = tk.StringVar(value="3333")
        make_entry(self.wifi_card, textvariable=self.wifi_port, width=8).grid(
            row=2, column=1, sticky="w", padx=8)
        make_label(self.wifi_card, "(default: 3333)",
                   fg=FG_DIM).grid(row=2, column=2, sticky="w", padx=4)

        make_button(self.wifi_card, "🔍  Scan on LAN",
                    self._scan_lan, accent=False).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(10, 2))

        # ── Serial Settings Card ──────────────────────────────────────
        self.serial_card = make_card(self, padx=20, pady=14)
        self.serial_card.columnconfigure(1, weight=1)
        self.serial_card.grid(row=2, column=0, sticky="ew", padx=20, pady=4)

        make_label(self.serial_card, "🔌  USB Serial Settings",
                   font=FONT_HDR).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        make_label(self.serial_card, "COM Port:").grid(
            row=1, column=0, sticky="w", pady=5)
        self.serial_port_var = tk.StringVar()
        self.serial_port_cb = ttk.Combobox(
            self.serial_card, textvariable=self.serial_port_var,
            state="readonly", width=18, font=FONT_UI)
        self.serial_port_cb.grid(row=1, column=1, sticky="w", padx=8)
        make_button(self.serial_card, "🔄", self._refresh_ports,
                    accent=False).grid(row=1, column=2, padx=(4, 0))

        make_label(self.serial_card, "Baudrate:").grid(
            row=2, column=0, sticky="w", pady=5)
        self.serial_baud = tk.StringVar(value="115200")
        baud_frame = tk.Frame(self.serial_card, bg=BG_CARD)
        baud_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=8)
        for baud in ["9600", "57600", "115200", "230400"]:
            tk.Radiobutton(
                baud_frame, text=baud, variable=self.serial_baud, value=baud,
                bg=BG_CARD, fg=FG, selectcolor=BG, activebackground=BG_CARD
            ).pack(side="left", padx=(0, 10))

        # pre-populate ports and hide serial card initially
        self._refresh_ports()
        self.serial_card.grid_remove()

        # ── Action Buttons ────────────────────────────────────────────
        act_card = make_card(self, padx=20, pady=14)
        act_card.grid(row=3, column=0, sticky="ew", padx=20, pady=4)

        self.btn_connect = make_button(
            act_card, "  ⚡  Connect  ", self._connect)
        self.btn_connect.pack(side="left", padx=(0, 10))

        self.btn_disconnect = make_button(
            act_card, "  ✖  Disconnect  ", self._disconnect, accent=False)
        self.btn_disconnect.pack(side="left")
        self.btn_disconnect.config(state="disabled")

        # ── Status Panel ──────────────────────────────────────────────
        status_card = make_card(self, padx=20, pady=16)
        status_card.grid(row=4, column=0, sticky="ew", padx=20, pady=(8, 16))
        status_card.columnconfigure(1, weight=1)

        make_label(status_card, "Connection Status",
                   font=FONT_HDR).grid(row=0, column=0, columnspan=2,
                                        sticky="w", pady=(0, 12))

        # Dot indicator
        self.dot_label = make_label(
            status_card, "●", font=("Segoe UI", 22), fg=FG_LOG_ERR)
        self.dot_label.grid(row=1, column=0, rowspan=4, sticky="n", padx=(0, 14))

        # Status fields
        status_defs = [
            ("Status:",  "DISCONNECTED"),
            ("Mode:",    "—"),
            ("Target:",  "—"),
            ("Latency:", "—"),
            ("Device:",  "—"),
        ]
        self.status_vars: dict[str, tk.StringVar] = {}
        for i, (lbl, default) in enumerate(status_defs):
            make_label(status_card, lbl, fg=FG_DIM).grid(
                row=i + 1, column=1, sticky="w", pady=2)
            var = tk.StringVar(value=default)
            self.status_vars[lbl] = var
            # Create the value label directly — bound to the StringVar
            tk.Label(
                status_card, textvariable=var,
                bg=BG_CARD, fg=FG, font=FONT_MONO
            ).grid(row=i + 1, column=2, sticky="w", padx=8)

    # ------------------------------------------------------------------
    # Mode Switching
    # ------------------------------------------------------------------

    def _on_mode_change(self):
        if self.conn_mode.get() == "wifi":
            self.serial_card.grid_remove()
            self.wifi_card.grid(row=2, column=0, sticky="ew", padx=20, pady=4)
        else:
            self.wifi_card.grid_remove()
            self.serial_card.grid(row=2, column=0, sticky="ew", padx=20, pady=4)

    # ------------------------------------------------------------------
    # Port Detection
    # ------------------------------------------------------------------

    def _refresh_ports(self):
        def run():
            try:
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                port_list = [p.device for p in ports]
                if not port_list:
                    port_list = ["(none found)"]
                self.serial_port_cb["values"] = port_list
                self.serial_port_var.set(port_list[0])
                self.logger.info(f"Serial ports found: {', '.join(port_list)}")
            except ImportError:
                self.logger.warn("pyserial not installed — run: pip install pyserial")
            except Exception as ex:
                self.logger.err(f"Port scan failed: {ex}")
        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------
    # LAN Scan
    # ------------------------------------------------------------------

    def _scan_lan(self):
        def run():
            import socket
            self.logger.section("LAN Scan — Looking for ESP32")
            found_any = False

            hostnames = [
                "esp32.local",
                "esp32-ota.local",
                "esp32-gateway.local",
            ]
            for host in hostnames:
                try:
                    ip = socket.gethostbyname(host)
                    self.logger.ok(f"Found → {host}  =  {ip}")
                    self.wifi_ip.set(ip)
                    found_any = True
                except socket.gaierror:
                    self.logger.info(f"Not found: {host}")

            # Also try a quick ping sweep on local subnet
            if not found_any:
                self.logger.info("Trying ping on 192.168.1.x range ...")
                port = int(self.wifi_port.get() or "3333")
                for last_octet in range(1, 20):
                    ip = f"192.168.1.{last_octet}"
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(0.3)
                        s.connect((ip, port))
                        s.close()
                        self.logger.ok(f"  TCP port open: {ip}:{port}")
                        self.wifi_ip.set(ip)
                        found_any = True
                        break
                    except Exception:
                        pass

            if not found_any:
                self.logger.warn("No ESP32 found on LAN. Enter IP manually.")
        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------
    # Thread-safe UI helper
    # ------------------------------------------------------------------

    def _ui(self, func):
        """Schedule func() on the Tkinter main thread (thread-safe)."""
        self.after(0, func)

    # ------------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------------

    def _connect(self):
        CONN.close()
        mode = self.conn_mode.get()

        def run():
            # Disable button while connecting (main-thread safe)
            self._ui(lambda: self.btn_connect.config(
                state="disabled", text="Connecting…"))
            try:
                if mode == "wifi":
                    self._connect_wifi()
                else:
                    self._connect_serial()
            finally:
                if CONN.connected:
                    self._ui(lambda: [
                        self.btn_connect.config(
                            state="disabled", text="  ⚡  Connect  "),
                        self.btn_disconnect.config(state="normal"),
                    ])
                else:
                    self._ui(lambda: [
                        self.btn_connect.config(
                            state="normal", text="  ⚡  Connect  "),
                        self.btn_disconnect.config(state="disabled"),
                    ])
                self._ui(self._refresh_status_panel)

        threading.Thread(target=run, daemon=True).start()

    def _connect_wifi(self):
        import socket, time
        ip   = self.wifi_ip.get().strip()
        port = int(self.wifi_port.get().strip() or "3333")

        self.logger.section("WiFi Connect")
        self.logger.info(f"Connecting to {ip}:{port} …")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(4)

            t0 = time.monotonic()
            sock.connect((ip, port))
            latency = (time.monotonic() - t0) * 1000

            # Try PING handshake
            device_name = "ESP32-OTA-Gateway"
            try:
                sock.sendall(self.PING_MSG)
                resp = sock.recv(128)
                decoded = resp.strip().decode(errors="replace")
                if resp.startswith(self.PONG_PREFIX):
                    device_name = decoded
                    self.logger.ok(f"Handshake OK — {decoded}")
                else:
                    self.logger.warn(f"Unexpected response: {decoded!r} — connection accepted anyway")
            except socket.timeout:
                self.logger.warn("No handshake response (timeout) — port open, device assumed connected")

            CONN._socket    = sock
            CONN.connected  = True
            CONN.mode       = "wifi"
            CONN.target     = f"{ip}:{port}"
            CONN.latency_ms = latency
            CONN.device_name = device_name

            self.logger.ok(f"Connected via WiFi → {ip}:{port}")
            self.logger.ok(f"Latency: {latency:.1f} ms")

        except ConnectionRefusedError:
            self.logger.err(f"Connection refused — is ESP32 listening on {ip}:{port}?")
        except socket.timeout:
            self.logger.err(f"Timeout — no response from {ip}:{port} (check IP / firewall)")
        except OSError as e:
            self.logger.err(f"Network error: {e}")

    def _connect_serial(self):
        import time
        port  = self.serial_port_var.get().strip()
        baud  = int(self.serial_baud.get())

        self.logger.section("USB Serial Connect")
        self.logger.info(f"Opening {port} @ {baud} baud …")

        try:
            import serial
        except ImportError:
            self.logger.err("pyserial not installed — run: pip install pyserial")
            return

        try:
            ser = serial.Serial(port, baud, timeout=2)
            import time; time.sleep(0.5)  # let DTR reset settle

            device_name = "ESP32-OTA-Gateway"
            try:
                ser.write(self.AT_CMD)
                resp = ser.readline()
                decoded = resp.strip().decode(errors="replace")
                if self.AT_OK in resp:
                    self.logger.ok(f"AT handshake OK — {decoded}")
                    device_name = decoded or device_name
                else:
                    self.logger.warn(f"Response: {decoded!r} — port open, assumed connected")
            except serial.SerialTimeoutException:
                self.logger.warn("No handshake (timeout) — port open, device assumed connected")

            CONN._serial     = ser
            CONN.connected   = True
            CONN.mode        = "serial"
            CONN.target      = f"{port} @ {baud}"
            CONN.latency_ms  = 0.0
            CONN.device_name = device_name

            self.logger.ok(f"Connected via USB Serial → {port} @ {baud} baud")

        except serial.SerialException as e:
            self.logger.err(f"Serial error: {e}")
        except ValueError as e:
            self.logger.err(f"Invalid port: {e}")

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    def _disconnect(self):
        def run():
            mode = CONN.mode
            CONN.close()
            self.logger.section("Disconnected")
            self.logger.info(f"Connection closed ({mode})")
            self._ui(lambda: [
                self.btn_connect.config(state="normal", text="  ⚡  Connect  "),
                self.btn_disconnect.config(state="disabled"),
            ])
            self._ui(self._refresh_status_panel)
        threading.Thread(target=run, daemon=True).start()


    # ------------------------------------------------------------------
    # Status Panel Update
    # ------------------------------------------------------------------

    def _refresh_status_panel(self):
        if CONN.connected:
            self.dot_label.config(fg=FG_LOG_OK)
            self.status_vars["Status:"].set("CONNECTED")
            self.status_vars["Mode:"].set(CONN.mode.upper())
            self.status_vars["Target:"].set(CONN.target)
            lat = f"{CONN.latency_ms:.1f} ms" if CONN.mode == "wifi" else "N/A (Serial)"
            self.status_vars["Latency:"].set(lat)
            self.status_vars["Device:"].set(CONN.device_name or "Unknown")
        else:
            self.dot_label.config(fg=FG_LOG_ERR)
            self.status_vars["Status:"].set("DISCONNECTED")
            self.status_vars["Mode:"].set("—")
            self.status_vars["Target:"].set("—")
            self.status_vars["Latency:"].set("—")
            self.status_vars["Device:"].set("—")


# =============================================================================
# Main Application Window
# =============================================================================

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
        make_button(log_hdr, "Clear", lambda: logger.clear(), accent=False).pack(side="right")

        log_text = ScrolledText(log_frame, height=10, state="disabled",
                                bg="#0d1117", fg=FG, font=FONT_LOG,
                                relief="flat", borderwidth=0,
                                insertbackground=ACCENT,
                                highlightthickness=1, highlightbackground=BORDER)
        log_text.pack(fill="x")

        logger = Logger(log_text)

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

        # Notebook
        style.configure("Dark.TNotebook",
                        background=BG, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                        background=BG_PANEL, foreground=FG_DIM,
                        padding=(12, 6), font=FONT_UI, borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                        background=BORDER, troughcolor=BG_CARD,
                        arrowcolor=FG_DIM, bordercolor=BG_CARD)


    def _on_close(self):
        """Clean up connections before exit."""
        CONN.close()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
