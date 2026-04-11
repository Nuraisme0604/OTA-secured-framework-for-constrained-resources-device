"""
manifest_builder.py - OTA Manifest Builder

Creates and signs OTA manifests for firmware updates.
"""

import struct
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from crypto_utils import (
    ed25519_sign, 
    ed25519_load_private_key,
    generate_random_bytes,
    ED25519_SIGNATURE_SIZE
)


# =============================================================================
# Constants (must match manifest_def.h)
# =============================================================================

MANIFEST_MAGIC = 0x4F54414D  # "MOTA" in little-endian
MANIFEST_VERSION_MAJOR = 1
MANIFEST_VERSION_MINOR = 0

FW_HASH_SIZE = 32
SIGNATURE_SIZE = 64
NONCE_SIZE = 16
VENDOR_ID_SIZE = 4
DEVICE_CLASS_SIZE = 2


@dataclass
class ManifestConfig:
    """Configuration for manifest generation"""
    vendor_id: bytes          # 4 bytes
    device_class: bytes       # 2 bytes
    device_id: int            # 0 = broadcast
    fw_version: int           # Semantic version packed as uint32
    security_version: int     # Anti-rollback counter
    chunk_size: int = 1024    # Default 1KB chunks
    entry_point: int = 0x08003000  # Default STM32 app entry point


def compute_firmware_hash(firmware_data: bytes) -> bytes:
    """Compute SHA-256 hash of firmware."""
    return hashlib.sha256(firmware_data).digest()


def pack_version(major: int, minor: int, patch: int, build: int = 0) -> int:
    """Pack semantic version into uint32: major.minor.patch.build"""
    return (major << 24) | (minor << 16) | (patch << 8) | build


def unpack_version(version: int) -> tuple:
    """Unpack uint32 version to (major, minor, patch, build)"""
    return (
        (version >> 24) & 0xFF,
        (version >> 16) & 0xFF,
        (version >> 8) & 0xFF,
        version & 0xFF
    )


class ManifestBuilder:
    """Builder for OTA firmware manifests."""
    
    MANIFEST_FORMAT = "<" + "".join([
        "I",      # magic (4)
        "B",      # version_major (1)
        "B",      # version_minor (1)
        "H",      # header_size (2)
        f"{VENDOR_ID_SIZE}s",    # vendor_id (4)
        f"{DEVICE_CLASS_SIZE}s", # device_class (2)
        "I",      # device_id (4)
        "I",      # fw_version (4)
        "I",      # fw_size (4)
        "I",      # fw_entry_point (4)
        "H",      # chunk_size (2)
        "H",      # total_chunks (2)
        "I",      # security_version (4)
        "I",      # build_timestamp (4)
        f"{FW_HASH_SIZE}s",      # fw_hash (32)
        f"{NONCE_SIZE}s",        # nonce_base (16)
        f"{SIGNATURE_SIZE}s",    # signature (64)
    ])
    
    MANIFEST_SIZE = struct.calcsize(MANIFEST_FORMAT)
    SIGNED_SIZE = MANIFEST_SIZE - SIGNATURE_SIZE
    
    def __init__(self, config: ManifestConfig, private_key_path: Optional[str] = None):
        """
        Initialize manifest builder.
        
        Args:
            config: Manifest configuration
            private_key_path: Path to Ed25519 private key PEM file
        """
        self.config = config
        self.private_key: Optional[bytes] = None
        
        if private_key_path:
            self.private_key = ed25519_load_private_key(private_key_path)
    
    def set_private_key(self, private_key: bytes):
        """Set Ed25519 private key for signing."""
        self.private_key = private_key
    
    def build(self, firmware_data: bytes) -> bytes:
        """
        Build and sign a manifest for the given firmware.
        
        Args:
            firmware_data: Raw firmware binary data
        
        Returns:
            Packed manifest bytes (ready to send to device)
        """
        if self.private_key is None:
            raise ValueError("Private key not set. Call set_private_key() first.")
        
        # Calculate derived values
        fw_hash = compute_firmware_hash(firmware_data)
        fw_size = len(firmware_data)
        total_chunks = (fw_size + self.config.chunk_size - 1) // self.config.chunk_size
        nonce_base = generate_random_bytes(NONCE_SIZE)
        build_timestamp = int(time.time())
        
        # Pack manifest without signature
        manifest_unsigned = struct.pack(
            self.MANIFEST_FORMAT[:-f"{SIGNATURE_SIZE}s".count('s') - len(f"{SIGNATURE_SIZE}s")],
            MANIFEST_MAGIC,
            MANIFEST_VERSION_MAJOR,
            MANIFEST_VERSION_MINOR,
            self.MANIFEST_SIZE,
            self.config.vendor_id,
            self.config.device_class,
            self.config.device_id,
            self.config.fw_version,
            fw_size,
            self.config.entry_point,
            self.config.chunk_size,
            total_chunks,
            self.config.security_version,
            build_timestamp,
            fw_hash,
            nonce_base,
        )
        
        # Pad to SIGNED_SIZE if needed
        if len(manifest_unsigned) < self.SIGNED_SIZE:
            manifest_unsigned += b'\x00' * (self.SIGNED_SIZE - len(manifest_unsigned))
        
        # Sign the manifest
        signature = ed25519_sign(self.private_key, manifest_unsigned[:self.SIGNED_SIZE])
        
        # Complete manifest
        manifest = manifest_unsigned[:self.SIGNED_SIZE] + signature
        
        return manifest
    
    def build_from_file(self, firmware_path: str) -> bytes:
        """Build manifest from firmware file."""
        with open(firmware_path, "rb") as f:
            firmware_data = f.read()
        return self.build(firmware_data)
    
    def save_manifest(self, manifest: bytes, output_path: str):
        """Save manifest to file."""
        with open(output_path, "wb") as f:
            f.write(manifest)
        print(f"Manifest saved to: {output_path}")
    
    @staticmethod
    def parse_manifest(manifest_data: bytes) -> dict:
        """Parse a manifest and return its fields as a dictionary."""
        if len(manifest_data) < ManifestBuilder.MANIFEST_SIZE:
            raise ValueError("Manifest data too short")
        
        fields = struct.unpack(ManifestBuilder.MANIFEST_FORMAT, 
                               manifest_data[:ManifestBuilder.MANIFEST_SIZE])
        
        return {
            "magic": hex(fields[0]),
            "version_major": fields[1],
            "version_minor": fields[2],
            "header_size": fields[3],
            "vendor_id": fields[4].hex(),
            "device_class": fields[5].hex(),
            "device_id": fields[6],
            "fw_version": unpack_version(fields[7]),
            "fw_size": fields[8],
            "fw_entry_point": hex(fields[9]),
            "chunk_size": fields[10],
            "total_chunks": fields[11],
            "security_version": fields[12],
            "build_timestamp": fields[13],
            "fw_hash": fields[14].hex(),
            "nonce_base": fields[15].hex(),
            "signature": fields[16].hex()[:32] + "...",
        }


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="OTA Manifest Builder")
    parser.add_argument("firmware", help="Path to firmware binary")
    parser.add_argument("-o", "--output", default="manifest.bin", 
                        help="Output manifest file")
    parser.add_argument("-k", "--key", required=True,
                        help="Path to Ed25519 private key PEM")
    parser.add_argument("--vendor", default="ACME", help="Vendor ID (4 chars)")
    parser.add_argument("--device-class", default="F1", help="Device class (2 chars)")
    parser.add_argument("--version", default="1.0.0", help="Firmware version (x.y.z)")
    parser.add_argument("--security-version", type=int, default=1,
                        help="Security counter for anti-rollback")
    
    args = parser.parse_args()
    
    # Parse version
    ver_parts = args.version.split(".")
    fw_version = pack_version(
        int(ver_parts[0]) if len(ver_parts) > 0 else 1,
        int(ver_parts[1]) if len(ver_parts) > 1 else 0,
        int(ver_parts[2]) if len(ver_parts) > 2 else 0
    )
    
    config = ManifestConfig(
        vendor_id=args.vendor.encode()[:VENDOR_ID_SIZE].ljust(VENDOR_ID_SIZE, b'\x00'),
        device_class=args.device_class.encode()[:DEVICE_CLASS_SIZE].ljust(DEVICE_CLASS_SIZE, b'\x00'),
        device_id=0,  # Broadcast
        fw_version=fw_version,
        security_version=args.security_version
    )
    
    builder = ManifestBuilder(config, args.key)
    manifest = builder.build_from_file(args.firmware)
    builder.save_manifest(manifest, args.output)
    
    # Print manifest info
    print("\nManifest Info:")
    info = ManifestBuilder.parse_manifest(manifest)
    for key, value in info.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
