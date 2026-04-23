"""Connection controller — WiFi/TCP and USB-Serial transport management."""

import socket
import time

from ..models.connection_state import CONN


PING_MSG    = b"PING\r\n"
PONG_PREFIX = b"PONG"
AT_CMD      = b"AT\r\n"
AT_OK       = b"OK"


def list_serial_ports(logger) -> list[str]:
    """Return list of detected serial-port device names."""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        port_list = [p.device for p in ports]
        if not port_list:
            port_list = ["(none found)"]
        logger.info(f"Serial ports found: {', '.join(port_list)}")
        return port_list
    except ImportError:
        logger.warn("pyserial not installed — run: pip install pyserial")
        return ["(none found)"]
    except Exception as ex:
        logger.err(f"Port scan failed: {ex}")
        return ["(none found)"]


def scan_lan(default_port: int, logger) -> str | None:
    """Scan for an ESP32 on common mDNS names + 192.168.1.x range.

    Returns the discovered IP string, or None if nothing found.
    """
    logger.section("LAN Scan — Looking for ESP32")

    for host in ("esp32.local", "esp32-ota.local", "esp32-gateway.local"):
        try:
            ip = socket.gethostbyname(host)
            logger.ok(f"Found → {host}  =  {ip}")
            return ip
        except socket.gaierror:
            logger.info(f"Not found: {host}")

    logger.info("Trying ping on 192.168.1.x range ...")
    for last_octet in range(1, 20):
        ip = f"192.168.1.{last_octet}"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect((ip, default_port))
            s.close()
            logger.ok(f"  TCP port open: {ip}:{default_port}")
            return ip
        except Exception:
            pass

    logger.warn("No ESP32 found on LAN. Enter IP manually.")
    return None


def connect_wifi(ip: str, port: int, logger) -> bool:
    """Open TCP connection to ESP32; update CONN. Returns True on success."""
    logger.section("WiFi Connect")
    logger.info(f"Connecting to {ip}:{port} …")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(4)

        t0 = time.monotonic()
        sock.connect((ip, port))
        latency = (time.monotonic() - t0) * 1000

        device_name = "ESP32-OTA-Gateway"
        try:
            sock.sendall(PING_MSG)
            resp = sock.recv(128)
            decoded = resp.strip().decode(errors="replace")
            if resp.startswith(PONG_PREFIX):
                device_name = decoded
                logger.ok(f"Handshake OK — {decoded}")
            else:
                logger.warn(f"Unexpected response: {decoded!r} — connection accepted anyway")
        except socket.timeout:
            logger.warn("No handshake response (timeout) — port open, device assumed connected")

        CONN._socket    = sock
        CONN.connected  = True
        CONN.mode       = "wifi"
        CONN.target     = f"{ip}:{port}"
        CONN.latency_ms = latency
        CONN.device_name = device_name

        logger.ok(f"Connected via WiFi → {ip}:{port}")
        logger.ok(f"Latency: {latency:.1f} ms")
        return True

    except ConnectionRefusedError:
        logger.err(f"Connection refused — is ESP32 listening on {ip}:{port}?")
    except socket.timeout:
        logger.err(f"Timeout — no response from {ip}:{port} (check IP / firewall)")
    except OSError as e:
        logger.err(f"Network error: {e}")
    return False


def connect_serial(port: str, baud: int, logger) -> bool:
    """Open pyserial connection; update CONN. Returns True on success."""
    logger.section("USB Serial Connect")
    logger.info(f"Opening {port} @ {baud} baud …")

    try:
        import serial
    except ImportError:
        logger.err("pyserial not installed — run: pip install pyserial")
        return False

    try:
        ser = serial.Serial(port, baud, timeout=2)
        time.sleep(0.5)  # let DTR reset settle

        device_name = "ESP32-OTA-Gateway"
        try:
            ser.write(AT_CMD)
            resp = ser.readline()
            decoded = resp.strip().decode(errors="replace")
            if AT_OK in resp:
                logger.ok(f"AT handshake OK — {decoded}")
                device_name = decoded or device_name
            else:
                logger.warn(f"Response: {decoded!r} — port open, assumed connected")
        except serial.SerialTimeoutException:
            logger.warn("No handshake (timeout) — port open, device assumed connected")

        CONN._serial     = ser
        CONN.connected   = True
        CONN.mode        = "serial"
        CONN.target      = f"{port} @ {baud}"
        CONN.latency_ms  = 0.0
        CONN.device_name = device_name

        logger.ok(f"Connected via USB Serial → {port} @ {baud} baud")
        return True

    except serial.SerialException as e:
        logger.err(f"Serial error: {e}")
    except ValueError as e:
        logger.err(f"Invalid port: {e}")
    return False


def disconnect(logger) -> str:
    """Close the active connection. Returns the previous mode string."""
    mode = CONN.mode
    CONN.close()
    logger.section("Disconnected")
    logger.info(f"Connection closed ({mode})")
    return mode
