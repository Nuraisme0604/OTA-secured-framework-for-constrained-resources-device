"""Key generation controller — Ed25519 / X25519 key pairs."""

from pathlib import Path


def generate_ed25519(dest_dir: Path, prefix: str, logger) -> str:
    """Generate an Ed25519 key pair, save PEM/bin/hex, return public-key hex."""
    from crypto_utils import ed25519_generate_keypair
    from cryptography.hazmat.primitives.asymmetric import ed25519 as ed
    from cryptography.hazmat.primitives import serialization

    logger.section("Generate Ed25519 Key Pair")
    kp = ed25519_generate_keypair()
    dest = Path(dest_dir)
    prefix = (prefix or "").strip() or "server_ed25519"

    # Private key as PEM (PKCS8, unencrypted)
    priv_pem_path = dest / f"{prefix}_private.pem"
    priv_key_obj = ed.Ed25519PrivateKey.from_private_bytes(kp.private_key)
    pem_bytes = priv_key_obj.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    priv_pem_path.write_bytes(pem_bytes)

    # Public key as raw bin + hex
    pub_path = dest / f"{prefix}_public.bin"
    pub_path.write_bytes(kp.public_key)
    pub_hex_path = dest / f"{prefix}_public.hex"
    pub_hex_path.write_text(kp.public_key.hex())

    logger.ok(f"Private key (PEM) → {priv_pem_path}")
    logger.ok(f"Public key (bin)  → {pub_path}")
    logger.ok(f"Public key (hex)  → {pub_hex_path}")
    logger.info(f"Public key: {kp.public_key.hex()}")
    return kp.public_key.hex()


def generate_x25519(dest_dir: Path, prefix: str, logger) -> str:
    """Generate an X25519 key pair, save raw bin + hex, return public-key hex."""
    from crypto_utils import x25519_generate_keypair

    logger.section("Generate X25519 Key Pair")
    kp = x25519_generate_keypair()
    dest = Path(dest_dir)
    prefix = (prefix or "").strip() or "server_x25519"

    priv_path = dest / f"{prefix}_private.bin"
    priv_path.write_bytes(kp.private_key)

    pub_path = dest / f"{prefix}_public.bin"
    pub_path.write_bytes(kp.public_key)
    pub_hex_path = dest / f"{prefix}_public.hex"
    pub_hex_path.write_text(kp.public_key.hex())

    logger.ok(f"Private key (bin) → {priv_path}")
    logger.ok(f"Public key (bin)  → {pub_path}")
    logger.ok(f"Public key (hex)  → {pub_hex_path}")
    logger.info(f"Public key: {kp.public_key.hex()}")
    return kp.public_key.hex()
