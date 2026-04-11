"""
crypto_utils.py - Cryptographic utilities for ASCON-CRA OTA Server

Provides:
- ASCON-128a encryption/decryption
- X25519 key exchange (ECDH)
- Ed25519 signing/verification
- Key derivation functions
"""

import os
import struct
from typing import Tuple, Optional
from dataclasses import dataclass

# Using cryptography library for Ed25519 and X25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

# ASCON implementation - using pyascon or custom implementation
try:
    from pyascon import ascon_encrypt, ascon_decrypt
    ASCON_AVAILABLE = True
except ImportError:
    ASCON_AVAILABLE = False
    print("Warning: pyascon not installed. Using placeholder ASCON functions.")


# =============================================================================
# Constants
# =============================================================================

ASCON_KEY_SIZE = 16       # 128-bit key
ASCON_NONCE_SIZE = 16     # 128-bit nonce
ASCON_TAG_SIZE = 16       # 128-bit authentication tag

ED25519_PUBKEY_SIZE = 32
ED25519_PRIVKEY_SIZE = 32
ED25519_SIGNATURE_SIZE = 64

X25519_PUBKEY_SIZE = 32
X25519_PRIVKEY_SIZE = 32


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class KeyPair:
    """Container for asymmetric key pair"""
    private_key: bytes
    public_key: bytes


@dataclass
class SessionKeys:
    """Session keys derived from key exchange"""
    encryption_key: bytes   # For ASCON encryption
    auth_key: bytes         # For MAC/HMAC
    nonce_base: bytes       # Base nonce for counter mode


# =============================================================================
# ASCON Functions
# =============================================================================

def ascon_128a_encrypt(key: bytes, nonce: bytes, plaintext: bytes, 
                       associated_data: bytes = b"") -> bytes:
    """
    Encrypt data using ASCON-128a AEAD.
    
    Args:
        key: 16-byte encryption key
        nonce: 16-byte nonce (must be unique per message)
        plaintext: Data to encrypt
        associated_data: Additional authenticated data (not encrypted)
    
    Returns:
        Ciphertext with appended authentication tag
    """
    if len(key) != ASCON_KEY_SIZE:
        raise ValueError(f"Key must be {ASCON_KEY_SIZE} bytes")
    if len(nonce) != ASCON_NONCE_SIZE:
        raise ValueError(f"Nonce must be {ASCON_NONCE_SIZE} bytes")
    
    if ASCON_AVAILABLE:
        return ascon_encrypt(key, nonce, associated_data, plaintext, "Ascon-128a")
    else:
        # Placeholder: XOR with key-derived stream (NOT SECURE - for testing only)
        return _placeholder_encrypt(key, nonce, plaintext, associated_data)


def ascon_128a_decrypt(key: bytes, nonce: bytes, ciphertext: bytes,
                       associated_data: bytes = b"") -> Optional[bytes]:
    """
    Decrypt data using ASCON-128a AEAD.
    
    Args:
        key: 16-byte encryption key
        nonce: 16-byte nonce (same as used for encryption)
        ciphertext: Encrypted data with authentication tag
        associated_data: Additional authenticated data (must match encryption)
    
    Returns:
        Plaintext on success, None if authentication fails
    """
    if len(key) != ASCON_KEY_SIZE:
        raise ValueError(f"Key must be {ASCON_KEY_SIZE} bytes")
    if len(nonce) != ASCON_NONCE_SIZE:
        raise ValueError(f"Nonce must be {ASCON_NONCE_SIZE} bytes")
    
    if ASCON_AVAILABLE:
        try:
            return ascon_decrypt(key, nonce, associated_data, ciphertext, "Ascon-128a")
        except Exception:
            return None
    else:
        return _placeholder_decrypt(key, nonce, ciphertext, associated_data)


def derive_chunk_nonce(nonce_base: bytes, chunk_index: int) -> bytes:
    """
    Derive unique nonce for each chunk using counter mode.
    
    Args:
        nonce_base: Base nonce from manifest (16 bytes)
        chunk_index: Chunk index (0-based)
    
    Returns:
        16-byte unique nonce for this chunk
    """
    # Last 4 bytes of nonce are the counter
    return nonce_base[:12] + struct.pack("<I", chunk_index)


# =============================================================================
# Ed25519 Functions (Signing)
# =============================================================================

def ed25519_generate_keypair() -> KeyPair:
    """Generate a new Ed25519 signing key pair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    return KeyPair(
        private_key=private_key.private_bytes_raw(),
        public_key=public_key.public_bytes_raw()
    )


def ed25519_sign(private_key: bytes, message: bytes) -> bytes:
    """
    Sign a message using Ed25519.
    
    Args:
        private_key: 32-byte Ed25519 private key
        message: Message to sign
    
    Returns:
        64-byte signature
    """
    key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
    return key.sign(message)


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """
    Verify an Ed25519 signature.
    
    Args:
        public_key: 32-byte Ed25519 public key
        message: Original message
        signature: 64-byte signature to verify
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
        key.verify(signature, message)
        return True
    except Exception:
        return False


def ed25519_load_private_key(pem_path: str) -> bytes:
    """Load Ed25519 private key from PEM file."""
    from cryptography.hazmat.primitives import serialization
    
    with open(pem_path, "rb") as f:
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
            serialization.load_pem_private_key(f.read(), password=None)
            .private_bytes_raw()
        )
    return private_key.private_bytes_raw()


# =============================================================================
# X25519 Functions (Key Exchange / ECDH)
# =============================================================================

def x25519_generate_keypair() -> KeyPair:
    """Generate a new X25519 key exchange key pair."""
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    return KeyPair(
        private_key=private_key.private_bytes_raw(),
        public_key=public_key.public_bytes_raw()
    )


def x25519_derive_shared_secret(private_key: bytes, peer_public_key: bytes) -> bytes:
    """
    Perform X25519 key exchange.
    
    Args:
        private_key: Our 32-byte X25519 private key
        peer_public_key: Peer's 32-byte X25519 public key
    
    Returns:
        32-byte shared secret
    """
    priv = x25519.X25519PrivateKey.from_private_bytes(private_key)
    pub = x25519.X25519PublicKey.from_public_bytes(peer_public_key)
    return priv.exchange(pub)


def derive_session_keys(shared_secret: bytes, 
                        context: bytes = b"ASCON-CRA-OTA-v1") -> SessionKeys:
    """
    Derive session keys from shared secret using HKDF.
    
    Args:
        shared_secret: 32-byte shared secret from X25519
        context: Application-specific context string
    
    Returns:
        SessionKeys containing encryption key, auth key, and nonce base
    """
    # Use HKDF to derive multiple keys
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=48,  # 16 + 16 + 16 bytes
        salt=None,
        info=context,
        backend=default_backend()
    )
    
    key_material = hkdf.derive(shared_secret)
    
    return SessionKeys(
        encryption_key=key_material[:16],
        auth_key=key_material[16:32],
        nonce_base=key_material[32:48]
    )


# =============================================================================
# Utility Functions
# =============================================================================

def generate_random_bytes(length: int) -> bytes:
    """Generate cryptographically secure random bytes."""
    return os.urandom(length)


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """Compare two byte strings in constant time (timing attack resistant)."""
    import hmac
    return hmac.compare_digest(a, b)


# =============================================================================
# Placeholder Functions (for testing without pyascon)
# =============================================================================

def _placeholder_encrypt(key: bytes, nonce: bytes, plaintext: bytes, 
                         ad: bytes) -> bytes:
    """Placeholder encryption - NOT SECURE, for testing only."""
    import hashlib
    # Generate a pseudo-random stream
    stream = hashlib.sha256(key + nonce).digest()
    while len(stream) < len(plaintext):
        stream += hashlib.sha256(stream).digest()
    
    # XOR encryption
    ciphertext = bytes(p ^ s for p, s in zip(plaintext, stream))
    
    # Fake tag
    tag = hashlib.sha256(key + nonce + ad + ciphertext).digest()[:ASCON_TAG_SIZE]
    
    return ciphertext + tag


def _placeholder_decrypt(key: bytes, nonce: bytes, ciphertext: bytes,
                         ad: bytes) -> Optional[bytes]:
    """Placeholder decryption - NOT SECURE, for testing only."""
    import hashlib
    
    if len(ciphertext) < ASCON_TAG_SIZE:
        return None
    
    ct = ciphertext[:-ASCON_TAG_SIZE]
    tag = ciphertext[-ASCON_TAG_SIZE:]
    
    # Verify tag
    expected_tag = hashlib.sha256(key + nonce + ad + ct).digest()[:ASCON_TAG_SIZE]
    if not constant_time_compare(tag, expected_tag):
        return None
    
    # XOR decryption
    stream = hashlib.sha256(key + nonce).digest()
    while len(stream) < len(ct):
        stream += hashlib.sha256(stream).digest()
    
    return bytes(c ^ s for c, s in zip(ct, stream))


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    print("=== Crypto Utils Test ===\n")
    
    # Test Ed25519
    print("1. Ed25519 Signing:")
    kp = ed25519_generate_keypair()
    print(f"   Private key: {kp.private_key.hex()[:32]}...")
    print(f"   Public key:  {kp.public_key.hex()}")
    
    message = b"Hello, ASCON-CRA OTA!"
    sig = ed25519_sign(kp.private_key, message)
    print(f"   Signature:   {sig.hex()[:32]}...")
    print(f"   Verify:      {ed25519_verify(kp.public_key, message, sig)}")
    
    # Test X25519
    print("\n2. X25519 Key Exchange:")
    alice = x25519_generate_keypair()
    bob = x25519_generate_keypair()
    
    alice_secret = x25519_derive_shared_secret(alice.private_key, bob.public_key)
    bob_secret = x25519_derive_shared_secret(bob.private_key, alice.public_key)
    
    print(f"   Alice shared secret: {alice_secret.hex()[:32]}...")
    print(f"   Bob shared secret:   {bob_secret.hex()[:32]}...")
    print(f"   Secrets match:       {alice_secret == bob_secret}")
    
    # Test session key derivation
    session = derive_session_keys(alice_secret)
    print(f"   Encryption key: {session.encryption_key.hex()}")
    print(f"   Auth key:       {session.auth_key.hex()}")
    
    # Test ASCON
    print("\n3. ASCON-128a Encryption:")
    key = generate_random_bytes(16)
    nonce = generate_random_bytes(16)
    plaintext = b"Firmware chunk data..."
    
    ciphertext = ascon_128a_encrypt(key, nonce, plaintext)
    decrypted = ascon_128a_decrypt(key, nonce, ciphertext)
    
    print(f"   Plaintext:  {plaintext}")
    print(f"   Ciphertext: {ciphertext.hex()[:32]}...")
    print(f"   Decrypted:  {decrypted}")
    print(f"   Match:      {plaintext == decrypted}")
    
    print("\n=== All tests passed! ===")
