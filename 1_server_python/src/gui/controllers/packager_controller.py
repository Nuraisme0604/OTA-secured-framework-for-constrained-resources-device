"""Firmware packager controller — chunk + encrypt firmware into a .pkg."""

import os


def resolve_key(mode: str, hex_str: str) -> bytes:
    """Return 16-byte ASCON-128a key from mode='random'|'hex'."""
    from crypto_utils import generate_random_bytes
    if mode == "hex":
        cleaned = (hex_str or "").strip().replace(" ", "")
        if len(cleaned) != 32:
            raise ValueError("Hex key must be exactly 32 hex characters (16 bytes)")
        return bytes.fromhex(cleaned)
    return generate_random_bytes(16)


def package_firmware(fw_path: str, out_path: str, key: bytes,
                     chunk_size: int, baudrate: int, logger) -> str:
    """Split + encrypt firmware; log and return the key-hex used."""
    from crypto_utils import generate_random_bytes
    from packet_builder import PacketBuilder, calculate_transfer_time

    logger.section("Package Firmware")

    nonce_base = generate_random_bytes(16)

    logger.info(f"Firmware:    {fw_path}")
    logger.info(f"Output:      {out_path}")
    logger.info(f"Chunk size:  {chunk_size} bytes")
    logger.info(f"Key (hex):   {key.hex()}")
    logger.info(f"Nonce base:  {nonce_base.hex()}")

    builder = PacketBuilder(chunk_size=chunk_size)
    total_chunks, total_bytes = builder.package_firmware(
        fw_path, key, nonce_base, out_path)

    fw_size = os.path.getsize(fw_path)
    est_time = calculate_transfer_time(fw_size, chunk_size, baudrate)

    logger.ok(f"Package saved → {out_path}")
    logger.ok(f"Total chunks:  {total_chunks}")
    logger.ok(f"Encrypted bytes: {total_bytes:,}")
    logger.info(f"Estimated transfer @ {baudrate} baud: {est_time:.2f}s")
    logger.warn("⚠  Save the Key (hex) above — it's required by the "
                "device to decrypt the firmware!")
    return key.hex()


def estimate_transfer(fw_path: str, chunk_size: int, selected_baud: int, logger) -> None:
    """Log estimated transfer times across common baud rates."""
    from packet_builder import calculate_transfer_time

    fw_size = os.path.getsize(fw_path)

    logger.section("Transfer Time Estimate")
    logger.info(f"Firmware size: {fw_size:,} bytes ({fw_size/1024:.1f} KB)")
    logger.info(f"Chunk size:    {chunk_size} bytes")
    chunks = (fw_size + chunk_size - 1) // chunk_size
    logger.info(f"Total chunks:  {chunks}")

    for baud_rate in [9600, 57600, 115200, 230400]:
        t = calculate_transfer_time(fw_size, chunk_size, baud_rate)
        marker = "  ◀ selected" if baud_rate == selected_baud else ""
        logger.info(f"  @ {baud_rate:>6} baud → {t:6.2f}s{marker}")
