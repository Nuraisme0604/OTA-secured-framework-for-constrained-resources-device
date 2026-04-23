"""Reusable themed widget factories and file-dialog helpers."""

import tkinter as tk
from tkinter import filedialog

from .theme import (
    ACCENT, ACCENT_DIM, BG_CARD, BG_PANEL, BORDER, FG, FONT_MONO, FONT_UI,
)


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


def browse_dir(var: tk.StringVar, title="Select Output Directory"):
    d = filedialog.askdirectory(title=title)
    if d:
        var.set(d)
