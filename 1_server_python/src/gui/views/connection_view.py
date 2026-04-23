"""ESP32 Connection Manager tab — View."""

import threading
import tkinter as tk
from tkinter import ttk

from ..controllers import connection_controller
from ..logger import Logger
from ..models.connection_state import CONN
from ..theme import (
    BG, BG_CARD, FG, FG_DIM, FG_LOG_ERR, FG_LOG_OK, FONT_HDR, FONT_LARGE,
    FONT_MONO, FONT_UI,
)
from ..widgets import make_button, make_card, make_entry, make_label


class ESPConnectionTab(tk.Frame):
    """Manages the connection between this PC server and the ESP32 Gateway."""

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
            tk.Radiobutton(
                mode_frame, text=f"  {icon}  {label_txt}",
                variable=self.conn_mode, value=val,
                bg=BG_CARD, fg=FG, selectcolor=BG,
                activebackground=BG_CARD, font=FONT_UI,
                command=self._on_mode_change,
            ).pack(side="left", padx=(0, 24))

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
                bg=BG_CARD, fg=FG, selectcolor=BG, activebackground=BG_CARD,
            ).pack(side="left", padx=(0, 10))

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

        self.dot_label = make_label(
            status_card, "●", font=("Segoe UI", 22), fg=FG_LOG_ERR)
        self.dot_label.grid(row=1, column=0, rowspan=4, sticky="n", padx=(0, 14))

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
            tk.Label(
                status_card, textvariable=var,
                bg=BG_CARD, fg=FG, font=FONT_MONO,
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
    # Thread-safe UI helper
    # ------------------------------------------------------------------

    def _ui(self, func):
        """Schedule func() on the Tkinter main thread (thread-safe)."""
        self.after(0, func)

    # ------------------------------------------------------------------
    # Port / LAN discovery
    # ------------------------------------------------------------------

    def _refresh_ports(self):
        def run():
            ports = connection_controller.list_serial_ports(self.logger)
            self._ui(lambda: (
                self.serial_port_cb.configure(values=ports),
                self.serial_port_var.set(ports[0]),
            ))
        threading.Thread(target=run, daemon=True).start()

    def _scan_lan(self):
        def run():
            port = int(self.wifi_port.get() or "3333")
            ip = connection_controller.scan_lan(port, self.logger)
            if ip:
                self._ui(lambda: self.wifi_ip.set(ip))
        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------
    # Connect / Disconnect
    # ------------------------------------------------------------------

    def _connect(self):
        CONN.close()
        mode = self.conn_mode.get()

        def run():
            self._ui(lambda: self.btn_connect.config(
                state="disabled", text="Connecting…"))
            try:
                if mode == "wifi":
                    ip = self.wifi_ip.get().strip()
                    port = int(self.wifi_port.get().strip() or "3333")
                    connection_controller.connect_wifi(ip, port, self.logger)
                else:
                    port = self.serial_port_var.get().strip()
                    baud = int(self.serial_baud.get())
                    connection_controller.connect_serial(port, baud, self.logger)
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

    def _disconnect(self):
        def run():
            connection_controller.disconnect(self.logger)
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
