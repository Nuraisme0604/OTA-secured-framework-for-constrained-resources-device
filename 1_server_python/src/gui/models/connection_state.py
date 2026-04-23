"""Shared connection state (Model layer)."""


class ConnectionState:
    """Shared connection state accessible by all GUI tabs."""

    def __init__(self):
        self.connected: bool = False
        self.mode: str = ""          # 'wifi' or 'serial'
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


# Module-level singleton shared by controllers and views.
CONN = ConnectionState()
