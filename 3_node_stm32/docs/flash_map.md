# Flash Memory Layout for STM32F103 OTA Node

Tài liệu này mô tả bố trí flash cho node STM32 trong hệ OTA ASCON-CRA.
Thông số và địa chỉ phải nhất quán với
[`docs/technical/system_overview.md`](../../docs/technical/system_overview.md) §3.3,
[`docs/technical/pinout.md`](../../docs/technical/pinout.md) §6,
và struct định nghĩa trong `common/manifest_def.h` + `common/boot_metadata.h` (Q2 cần tạo).

---

## 1. Target: STM32F103C8T6 Blue Pill (128 KB Flash, 20 KB SRAM)

A/B dual-slot trên cùng một chip, metadata region đặt ở cuối flash với 2 bank ping-pong.

| Địa chỉ                       | Size  | Region                        | Mô tả                                                           |
|---|---|---|---|
| `0x0800_0000` – `0x0800_3FFF` | 16 KB | **Bootloader**                | Root of trust: verify manifest, chọn slot, VTOR jump           |
| `0x0800_4000` – `0x0801_0FFF` | 52 KB | **Application Slot A**        | Firmware đang chạy                                              |
| `0x0801_1000` – `0x0801_DFFF` | 52 KB | **Application Slot B**        | OTA staging (ghi chunk giải mã vào đây)                         |
| `0x0801_E000` – `0x0801_EFFF` | 4 KB  | **Boot Metadata Bank 0**      | `boot_metadata_t` — Q2 dùng bank này                            |
| `0x0801_F000` – `0x0801_FFFF` | 4 KB  | **Boot Metadata Bank 1**      | Ping-pong dự phòng — Q3 hardening                               |

Tổng: 16 + 52 + 52 + 4 + 4 = **128 KB** khớp đúng dung lượng flash. Page size 1 KB khớp
`chunk_size = 1024` B trong `ota_manifest_t`.

> Datasheet C8T6 chính thức ghi 64 KB, nhưng phần lớn Blue Pill thị trường có thực 128 KB
> dùng được (kiểm chứng bằng ST-Link). Linker script khai báo
> `FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 128K`. Phần cứng đã chốt — không xét fallback
> 64 KB.

---

## 2. Boot Flow

```
┌─────────────────┐
│  Hardware Reset │
└────────┬────────┘
         ▼
┌─────────────────────────────┐
│ Bootloader (0x0800_0000)    │
│  1. Khởi tạo IWDG           │
│  2. Đọc Metadata Bank 0     │
│     (0x0801_E000)           │
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
       │           │  - ASCON-Hash256(slot)     │
       │           │    == manifest.fw_hash     │
       │           └────────────┬───────────────┘
       │                        │ OK
       │                        ▼
       │           ┌────────────────────────────┐
       │           │ active_slot = pending_slot │
       │           │ security_counter ← new     │
       │           │ flags &= ~PENDING          │
       │           │ ghi metadata + CRC32       │
       │           └────────────┬───────────────┘
       ▼                        ▼
┌─────────────────────────────────────────────┐
│ __disable_irq() + stop SysTick + DMA        │
│ Set SCB->VTOR = active_slot_base            │
│ Jump to (active_slot_base + 4) — Reset_H    │
└─────────────────────────────────────────────┘
```

Nếu verify thất bại: `boot_attempts++`. Quá 3 lần → rollback về slot còn lại; ghi error code
nhóm `Boot (0xC0)` trong `common/error_codes.h`.

---

## 3. Boot Metadata Structure (4 KB @ Bank 0)

Đây là **metadata của bootloader**, khác với `ota_manifest_t` (firmware passport nằm trong
payload OTA, định nghĩa ở `common/manifest_def.h`).

```c
typedef struct {
    uint32_t magic;               // 0xB007F1A6 — nhận diện metadata hợp lệ
    uint32_t seq_counter;         // Số phiên bản metadata (Q3 ping-pong: bank lớn hơn = mới hơn)
    uint8_t  active_slot;         // 0 = Slot A, 1 = Slot B
    uint8_t  pending_slot;        // Slot đang chờ verify sau OTA
    uint8_t  boot_attempts;       // Đếm số lần boot thất bại (max 3)
    uint8_t  flags;               // PENDING | VERIFIED | ROLLBACK_DONE ...
    uint32_t security_counter;    // Anti-rollback: firmware mới phải ≥ giá trị này
    ota_manifest_t manifest_a;    // 212 bytes — manifest đã ký của Slot A
    ota_manifest_t manifest_b;    // 212 bytes — manifest đã ký của Slot B
    uint8_t  reserved[/* pad */]; // Padding tới 4 KB – 4 byte CRC
    uint32_t crc32;               // CRC32 của toàn bộ struct phía trên
} boot_metadata_t;
```

Sizing: scalar header ~16 B + `2 × sizeof(ota_manifest_t)` = 424 B → ~440 B nội dung,
padding tới `4096 - 4` B, kèm CRC32 cuối. Q2 chỉ dùng Bank 0; Q3 luân phiên Bank 0 ↔ Bank 1
theo `seq_counter` lớn hơn.

Header chung **`common/boot_metadata.h`** chưa tồn tại — Q2 cần tạo để bootloader +
application share cùng định nghĩa.

---

## 4. Anti-Rollback Protection

Đồng bộ với §6 của [system_overview.md](../../docs/technical/system_overview.md).

1. Mỗi firmware update yêu cầu `manifest.security_version ≥ boot_metadata.security_counter`.
2. Sau khi boot thành công slot mới, bootloader cập nhật
   `security_counter = manifest.security_version` rồi flush metadata (Q2: bank 0; Q3: ping-pong).
3. Ngăn downgrade ngay cả khi attacker có manifest cũ hợp lệ (Ed25519 OK) nhưng
   `security_version` thấp hơn.
4. Error code khi từ chối: `OTA_ERR_VERSION_ROLLBACK (0x80)` — nhóm `OTA (0x80)` trong
   `common/error_codes.h`. Chunk giả mạo phát hiện qua AEAD → `OTA_ERR_MAC_VERIFY_FAILED (0x43)`
   (nhóm `Crypto (0x40)`).

---

## 5. Watchdog Protection

- Bootloader bật Independent Watchdog (IWDG) trước khi jump vào application.
- Application phải kick watchdog định kỳ trong 30 s đầu; nếu không, MCU reset về bootloader.
- Sau khi app chạy ổn định đủ lâu (vd: 10 s), bootloader clear `PENDING` flag → slot coi
  là confirmed.
- Quá 3 lần `boot_attempts` liên tiếp → bootloader rollback sang slot còn lại và set error
  code nhóm `Boot (0xC0)`.

---

## 6. Power-fail Recovery (Q3)

Q2 chấp nhận giả định "không rút điện trong pha COMMIT" cho kịch bản demo. Q3 hardening:

- Ghi metadata 2-phase: ghi Bank mới trước (với `seq_counter` mới), kiểm CRC, mới đánh dấu
  bank cũ là invalid.
- Khi boot, nếu cả 2 bank cùng hợp lệ → chọn `seq_counter` lớn hơn.
- Nếu một bank corrupt (CRC fail) → tự động dùng bank còn lại, đánh dấu bank lỗi để overwrite
  lần ghi tiếp theo.

---

## 7. Tham chiếu chéo

- Layout cấp hệ thống + luồng OTA: [`docs/technical/system_overview.md`](../../docs/technical/system_overview.md) §3.3, §6
- Pinout chi tiết (UART, OLED, SWD): [`docs/technical/pinout.md`](../../docs/technical/pinout.md)
- `ota_manifest_t` (magic `0x4F54414D`, 212 B): `common/manifest_def.h`
- Packet types + error codes: `common/protocol_packet.h`, `common/error_codes.h`
- Linker script: `3_node_stm32/bootloader/STM32F103_Boot.ld`, `3_node_stm32/application/STM32F103_App.ld` (cần cập nhật MEMORY layout sang 16/52/52/8 ở Q2.1)
