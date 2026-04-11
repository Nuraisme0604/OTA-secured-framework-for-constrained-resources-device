"""
packet_builder.py - Firmware Packet Builder

Splits firmware into encrypted chunks for OTA transfer.
"""

import struct
from typing import List, Tuple, Iterator
from dataclasses import dataclass

from crypto_utils import (
    ascon_128a_encrypt,
    derive_chunk_nonce,
    ASCON_TAG_SIZE
)


@dataclass
class FirmwareChunk:
    """A single encrypted firmware chunk."""
    index: int
    total: int
    nonce: bytes
    encrypted_data: bytes
    
    def to_bytes(self) -> bytes:
        """Pack chunk for transmission."""
        return struct.pack(
            "<HHI",
            self.index,
            len(self.encrypted_data),
            self.index  # nonce counter
        ) + self.encrypted_data


class PacketBuilder:
    """Builds encrypted firmware packets for OTA transfer."""
    
    DEFAULT_CHUNK_SIZE = 1024
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize packet builder.
        
        Args:
            chunk_size: Size of each plaintext chunk (default 1024 bytes)
        """
        self.chunk_size = chunk_size
    
    def split_firmware(self, firmware_data: bytes) -> List[bytes]:
        """Split firmware into chunks."""
        chunks = []
        for i in range(0, len(firmware_data), self.chunk_size):
            chunks.append(firmware_data[i:i + self.chunk_size])
        return chunks
    
    def encrypt_firmware(self, firmware_data: bytes, 
                         encryption_key: bytes,
                         nonce_base: bytes) -> List[FirmwareChunk]:
        """
        Encrypt firmware into chunks.
        
        Args:
            firmware_data: Raw firmware binary
            encryption_key: 16-byte ASCON key
            nonce_base: 16-byte base nonce
        
        Returns:
            List of encrypted FirmwareChunk objects
        """
        chunks = self.split_firmware(firmware_data)
        total_chunks = len(chunks)
        
        encrypted_chunks = []
        for i, chunk in enumerate(chunks):
            nonce = derive_chunk_nonce(nonce_base, i)
            
            # Associated data includes chunk index for binding
            ad = struct.pack("<HH", i, total_chunks)
            
            encrypted = ascon_128a_encrypt(encryption_key, nonce, chunk, ad)
            
            encrypted_chunks.append(FirmwareChunk(
                index=i,
                total=total_chunks,
                nonce=nonce,
                encrypted_data=encrypted
            ))
        
        return encrypted_chunks
    
    def iter_encrypted_chunks(self, firmware_data: bytes,
                              encryption_key: bytes,
                              nonce_base: bytes) -> Iterator[FirmwareChunk]:
        """
        Iterate over encrypted chunks (memory efficient for large firmware).
        
        Yields:
            FirmwareChunk objects one at a time
        """
        chunks = self.split_firmware(firmware_data)
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            nonce = derive_chunk_nonce(nonce_base, i)
            ad = struct.pack("<HH", i, total_chunks)
            encrypted = ascon_128a_encrypt(encryption_key, nonce, chunk, ad)
            
            yield FirmwareChunk(
                index=i,
                total=total_chunks,
                nonce=nonce,
                encrypted_data=encrypted
            )
    
    def package_firmware(self, firmware_path: str,
                         encryption_key: bytes,
                         nonce_base: bytes,
                         output_path: str) -> Tuple[int, int]:
        """
        Read firmware, encrypt, and save as package file.
        
        Package format:
        [4 bytes: total_chunks][4 bytes: chunk_size]
        [For each chunk: 2 bytes length, encrypted data]
        
        Returns:
            Tuple of (total_chunks, total_bytes)
        """
        with open(firmware_path, "rb") as f:
            firmware_data = f.read()
        
        chunks = self.encrypt_firmware(firmware_data, encryption_key, nonce_base)
        
        with open(output_path, "wb") as f:
            # Header
            f.write(struct.pack("<II", len(chunks), self.chunk_size))
            
            # Chunks
            for chunk in chunks:
                f.write(struct.pack("<H", len(chunk.encrypted_data)))
                f.write(chunk.encrypted_data)
        
        total_bytes = sum(len(c.encrypted_data) for c in chunks)
        print(f"Packaged {len(chunks)} chunks ({total_bytes} bytes) to {output_path}")
        
        return len(chunks), total_bytes


def calculate_transfer_time(firmware_size: int, 
                            chunk_size: int = 1024,
                            baudrate: int = 115200,
                            overhead_percent: float = 0.2) -> float:
    """
    Estimate OTA transfer time.
    
    Args:
        firmware_size: Size of firmware in bytes
        chunk_size: Chunk size in bytes
        baudrate: UART baudrate
        overhead_percent: Protocol overhead (ACKs, retries, etc.)
    
    Returns:
        Estimated transfer time in seconds
    """
    # Each chunk has ASCON tag overhead
    encrypted_chunk_size = chunk_size + ASCON_TAG_SIZE
    
    # Number of chunks
    num_chunks = (firmware_size + chunk_size - 1) // chunk_size
    
    # Total data to transfer (with packet headers)
    total_bytes = num_chunks * (encrypted_chunk_size + 8)  # 8 bytes header
    
    # Add overhead
    total_bytes *= (1 + overhead_percent)
    
    # Transfer time (10 bits per byte at UART)
    transfer_time = (total_bytes * 10) / baudrate
    
    return transfer_time


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    from crypto_utils import generate_random_bytes
    
    print("=== Packet Builder Test ===\n")
    
    # Generate test data
    firmware = b"A" * 3000  # 3KB test firmware
    key = generate_random_bytes(16)
    nonce_base = generate_random_bytes(16)
    
    builder = PacketBuilder(chunk_size=1024)
    
    # Test chunking
    chunks = builder.split_firmware(firmware)
    print(f"Split into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}: {len(chunk)} bytes")
    
    # Test encryption
    encrypted = builder.encrypt_firmware(firmware, key, nonce_base)
    print(f"\nEncrypted {len(encrypted)} chunks")
    for chunk in encrypted:
        print(f"  Chunk {chunk.index}/{chunk.total}: {len(chunk.encrypted_data)} bytes")
    
    # Estimate transfer time
    transfer_time = calculate_transfer_time(len(firmware))
    print(f"\nEstimated transfer time @ 115200 baud: {transfer_time:.2f}s")
