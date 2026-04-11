# Flash Memory Layout for STM32F103 OTA System

## Overview

This document describes the flash memory partitioning for the ASCON-CRA OTA system
on STM32F103 microcontrollers.

## STM32F103C8 (64KB Flash, 20KB RAM)

| Address Range | Size | Region | Description |
|---------------|------|--------|-------------|
| 0x0800 0000 - 0x0800 2FFF | 12KB | Bootloader | Secure boot, signature verification |
| 0x0800 3000 - 0x0800 3FFF | 4KB | Metadata | Manifest, boot flags, security counter |
| 0x0800 4000 - 0x0800 FFFF | 48KB | Application | Main firmware (single slot) |

## STM32F103RC (256KB Flash, 48KB RAM) - For A/B Partitioning

| Address Range | Size | Region | Description |
|---------------|------|--------|-------------|
| 0x0800 0000 - 0x0800 3FFF | 16KB | Bootloader | Secure boot with A/B support |
| 0x0800 4000 - 0x0800 4FFF | 4KB | Metadata | Dual manifest, boot flags |
| 0x0800 5000 - 0x0801 FFFF | 108KB | Slot A | Primary application |
| 0x0802 0000 - 0x0803 AFFF | 108KB | Slot B | Secondary application (OTA target) |
| 0x0803 B000 - 0x0803 FFFF | 20KB | Reserved | Future use |

## Boot Flow

```
┌─────────────────┐
│  Hardware Reset │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Bootloader    │
│  (0x08000000)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Read Metadata  │────▶│ Validate Magic  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Select Active   │     │ Check Pending   │
│     Slot        │     │    Update       │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Verify Firmware │────▶│ Check Rollback  │
│   Signature     │     │   Protection    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Verify Firmware │────▶│ Jump to App     │
│     Hash        │     │  (0x08004000)   │
└─────────────────┘     └─────────────────┘
```

## Metadata Structure

```c
typedef struct {
    uint32_t magic;           // 0xB007F1A6
    uint8_t  active_slot;     // 0 = Slot A, 1 = Slot B
    uint8_t  pending_slot;    // Slot waiting for verification
    uint8_t  boot_attempts;   // Failed boot counter (max 3)
    uint8_t  flags;           // PENDING, VERIFIED, etc.
    uint32_t security_counter;// Anti-rollback counter
    ota_manifest_t manifest_a;// Manifest for Slot A
    ota_manifest_t manifest_b;// Manifest for Slot B
    uint32_t crc32;           // CRC32 of this structure
} boot_metadata_t;
```

## Anti-Rollback Protection

The `security_counter` field ensures that:
1. Each firmware update must have `security_version >= current_counter`
2. After successful boot, counter is updated to new firmware's security_version
3. Prevents downgrade attacks even with valid signatures

## Watchdog Protection

- Bootloader starts watchdog before jumping to app
- Application must refresh watchdog within 30 seconds
- If app fails to boot properly, watchdog resets to bootloader
- After 3 failed attempts, bootloader rolls back to previous slot
