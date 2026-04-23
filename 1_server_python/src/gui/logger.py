"""Logger widget — writes tagged messages into a ScrolledText."""

from datetime import datetime
from tkinter.scrolledtext import ScrolledText

from .theme import (
    FG, FG_DIM, FG_LOG_ERR, FG_LOG_INF, FG_LOG_OK, FG_LOG_WRN,
)


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

    def ok(self, msg):   self._write("OK ", msg, "OK")
    def err(self, msg):  self._write("ERR", msg, "ERR")
    def info(self, msg): self._write("INF", msg, "INF")
    def warn(self, msg): self._write("WRN", msg, "WRN")

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
