# Flash Memory Layout for STM32F103 OTA Node

Tài liệu này mô tả bố trí flash cho node STM32 trong hệ OTA ASCON-CRA.
Thông số và địa chỉ phải nhất quán với [`docs/technical/system_overview.md`](../../docs/technical/system_overview.md)
và các struct định nghĩa trong `common/manifest_def.h`.

---

## 1. Target: STM32F103C8T6 Blue Pill (128 KB Flash, 20 KB SRAM)

A/B dual-slot trên cùng một chip, metadata đặt ở cuối flash.

| Địa chỉ | Size | Region | Mô tả |
|---|---|---|---|
| `0x0800_0000` – `0x0800_3FFF` | 16 KB | **Bootloader**            | Root of trust, verify signature + hash, chọn slot |
| `0x0800_4000` – `0x0800_FFFF` | 48 KB | **Application Slot A**    | Firmware đang chạy |
| `0x0801_0000` – `0x0801_FBFF` | 48 KB | **Application Slot B**    | OTA staging slot (ghi chunk giải mã vào đây) |
| `0x0801_FC00` – `0x0801_FFFF` | 1 KB  | **Boot Metadata / Flags** | `boot_metadata_t`: active/pending slot, security counter, CRC |

> Lưu ý: Datasheet tiêu chuẩn ghi C8T6 = 64 KB, nhưng phần lớn chip trên thị trường Blue Pill thực sự có 128 KB flash dùng được (đã kiểm chứng bằng ST-Link). Linker script phải khai báo `FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 128K`. Nếu chip thật chỉ 64 KB, cần chuyển sang biến thể có đủ flash (VD: STM32F103CBT6) hoặc xem xét mô hình single-slot riêng.

---

## 2. Boot Flow

```
┌─────────────────┐
│  Hardware Reset │
└────────┬────────┘
         ▼
┌─────────────────────────────┐
│ Bootloader (0x0800_0000)    │
│  1. Khởi tạo watchdog       │
│  2. Đọc boot_metadata_t     │
│     (0x0801_FC00)           │
│  3. Verify CRC32 metadata   │
└────────┬────────────────────┘
         ▼
┌─────────────────────────────┐
│ Có pending slot?            │
└───┬─────────────────────┬───┘
    │ NO                  │ YES
    ▼                     ▼
┌──────────────┐   ┌────────────────────────────┐
│ Chọn         │   │ Verify manifest pending:   │
│ active_slot  │   │  - magic == 0x4F54414D     │
│ (A hoặc B)   │   │  - Ed25519 verify(signed)  │
└──────┬───────┘   │  - security_version ≥      │
       │           │    security_counter        │
       │           │  - SHA-256(app)=fw_hash    │
       │           └────────────┬───────────────┘
       │                        │ OK
       │                        ▼
       │           ┌────────────────────────────┐
       │           │ active_slot = pending_slot │
       │           │ security_counter ← new     │
       │           │ flags &= ~PENDING          │
       │           │ cập nhật CRC + flash       │
       │           └────────────┬───────────────┘
       ▼                        ▼
┌─────────────────────────────────────────────┐
│ Set VTOR = active_slot_base                 │
│ Jump to (active_slot_base + 4) — Reset_H    │
└─────────────────────────────────────────────┘
```

Nếu verify thất bại: `boot_attempts++`. Quá 3 lần → rollback về slot còn lại; ghi error code
theo nhóm `Boot (0xC0)` trong `common/error_codes.h`.

---

## 3. Boot Metadata Structure (1 KB @ 0x0801_FC00)

Đây là **metadata của bootloader**, khác với `ota_manifest_t` (firmware passport nằm trong
payload OTA, định nghĩa ở `common/manifest_def.h`).

```c
typedef struct {
    uint32_t magic;               // 0xB007F1A6 — nhận diện metadata hợp lệ
    uint8_t  active_slot;         // 0 = Slot A, 1 = Slot B
    uint8_t  pending_slot;        // Slot đang chờ verify sau OTA
    uint8_t  boot_attempts;       // Đếm số lần boot thất bại (max 3)
    uint8_t  flags;               // PENDING | VERIFIED | ROLLBACK_DONE ...
    uint32_t security_counter;    // Anti-rollback: firmware mới phải ≥ giá trị này
    ota_manifest_t manifest_a;    // 212 bytes — manifest đã ký của Slot A
    ota_manifest_t manifest_b;    // 212 bytes — manifest đã ký của Slot B
    uint8_t  reserved[...];       // Padding đến đủ 1 KB – 4 byte CRC
    uint32_t crc32;               // CRC32 của toàn bộ struct phía trên
} boot_metadata_t;
```

Sizing: `2 × sizeof(ota_manifest_t) = 424 bytes` + scalar ≈ 440 bytes, padding tới
`1024 - 4` bytes. Struct đầy đủ phải được định nghĩa ở header dùng chung giữa bootloader
và application (đề xuất thêm vào `common/boot_metadata.h` khi implement).

---

## 4. Anti-Rollback Protection

Đồng bộ với §6 của `system_overview.md`.

1. Mỗi firmware update yêu cầu `manifest.security_version ≥ boot_metadata.security_counter`.
2. Sau khi boot thành công một slot mới, bootloader cập nhật
   `security_counter = manifest.security_version` rồi flush metadata.
3. Ngăn downgrade ngay cả khi attacker có manifest cũ hợp lệ (Ed25519 OK) nhưng
   `security_version` thấp hơn.
4. Error code khi từ chối: `OTA_ERR_VERSION_ROLLBACK (0x80)` — nhóm `OTA (0x80)` trong
   `common/error_codes.h`. Chunk giả mạo phát hiện qua AEAD → `OTA_ERR_MAC_VERIFY_FAILED (0x43)`
   (nhóm `Crypto (0x40)`).

---

## 5. Watchdog Protection

- Bootloader bật Independent Watchdog (IWDG) trước khi jump vào application.
- Application phải kick watchdog định kỳ trong 30 s đầu; nếu không, MCU reset về bootloader.
- Sau khi app chạy ổn định đủ lâu, bootloader clear `PENDING` flag (slot coi là đã confirmed).
- Quá 3 lần `boot_attempts` liên tiếp → bootloader rollback sang slot còn lại và set error code
  nhóm `Boot (0xC0)`.

---

## 6. Tham chiếu chéo

- Layout ở cấp hệ thống + luồng OTA: [`docs/technical/system_overview.md`](../../docs/technical/system_overview.md) §3.3, §6
- `ota_manifest_t` (magic `0x4F54414D`, 212 bytes): `common/manifest_def.h`
- Packet types + error codes: `common/protocol_packet.h`, `common/error_codes.h`
- Linker script: `3_node_stm32/bootloader/STM32F103_Boot.ld`, `3_node_stm32/application/STM32F103_App.ld`
