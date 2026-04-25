# ASCON-CRA-OTA — Tài liệu kỹ thuật tổng quan

**Phiên bản:** 1.0  
**Ngày:** 2026-04-17  
**Tác giả:** Nhóm NCKH ASCON-CRA-OTA

---

## 1. Mục tiêu nghiên cứu

Xây dựng hệ thống OTA (Over-The-Air) firmware update bảo mật cho vi điều khiển STM32F103 tài nguyên thấp, sử dụng:

- **ASCON-128a** (NIST Lightweight Cryptography winner 2023) làm primitive chính cho xác thực và mã hóa.
- **Challenge-Response Authentication (CRA)** dựa trên ASCON-128a MAC để xác thực node trước khi nhận firmware.
- **Ed25519** ký manifest đảm bảo tính toàn vẹn và nguồn gốc firmware.
- **X25519 ECDH** trao đổi session key tạm thời.
- **Anti-rollback** dựa trên security version counter lưu trong flash metadata.

---

## 2. Kiến trúc hệ thống

```
   Server (PC, Python)
   ┌──────────────────┐
   │ key gen          │
   │ manifest sign    │
   │ chunk encrypt    │
   └────────┬─────────┘
            │ WiFi / TCP
            ▼
   Gateway (ESP32-S3 N16R8)
   ┌──────────────────┐
   │ WiFi STA +       │
   │ UART bridge +    │
   │ firmware cache   │
   └────────┬─────────┘
            │ UART1 115200 8N1
            ▼
   Node (STM32F103C8T6)               OLED 0.96"
   ┌──────────────────┐   I²C1       ┌─────────────┐
   │ OTA state mach.  │   400 kHz    │  SSD1306    │
   │ + bootloader     │◄────────────►│  128 × 64   │
   │ + crypto port    │  PB6 = SCK   │   mono      │
   │ + flash driver   │  PB7 = SDA   │             │
   └──────────────────┘              └─────────────┘
```

### 2.1 Thành phần

| Thành phần | Phần cứng | Thư mục | Vai trò |
|---|---|---|---|
| Server | PC (host) | `1_server_python/` | Tạo key, ký manifest, mã hóa firmware, GUI |
| Gateway | ESP32-S3 N16R8 | `2_gateway_esp32/` | Cầu nối WiFi↔UART, relay OTA session |
| Node | STM32F103C8T6 | `3_node_stm32/` | Nhận, xác thực, giải mã, ghi flash, boot |

### 2.2 Luồng OTA tổng quát

```
Server                    Gateway                   Node
  │                          │                        │
  │── POST /ota/start ──────►│                        │
  │                          │── PKT_HELLO ──────────►│
  │                          │◄── PKT_CHALLENGE ──────│  (32-byte nonce)
  │                          │── PKT_RESPONSE ───────►│  (ASCON-128a MAC)
  │                          │◄── PKT_SESSION_KEY ────│  (X25519 pubkey)
  │                          │── PKT_MANIFEST ───────►│  (ota_manifest_t)
  │                          │◄── ACK ────────────────│  (Ed25519 verify OK)
  │                          │── PKT_FW_CHUNK[0..N] ─►│  (ASCON-128a encrypted)
  │                          │◄── ACK[i] ─────────────│  (per chunk)
  │                          │── PKT_FW_VERIFY ──────►│
  │                          │◄── PKT_FW_VERIFY(res) ─│  (ASCON-Hash256 check)
  │                          │── PKT_FW_COMMIT ──────►│
  │                          │                        │── reboot → bootloader
  │                          │                        │── validate slot B
  │                          │                        │── swap A↔B → run
```

---

## 3. Phần cứng

### 3.1 Danh sách linh kiện

| Thiết bị | Thông số | Vai trò |
|---|---|---|
| ESP32-S3 N16R8 | 240 MHz dual-core, 16 MB Flash, 8 MB PSRAM, WiFi 2.4 GHz, BLE5 | Gateway |
| STM32F103C8T6 Blue Pill | 72 MHz Cortex-M3, 128 KB Flash, 20 KB SRAM | OTA Node |
| OLED 0.96" SSD1306 | 128×64 I²C, 3.3 V/5 V, driver SSD1306 | Demo payload + status display (Q2 — bắt buộc) |
| Logic Analyzer 8ch | 24 MHz max, 1.8–5.5 V, USB | Đo timing crypto (TN4) |
| ST-Link Mini V2 | SWD | Nạp/debug STM32 |
| CP2102 / CH340 | USB-Serial | Debug UART (tuỳ chọn) |

### 3.2 Kết nối phần cứng

```
ESP32-S3 (GPIO17) ──TX──► STM32 PA10 (USART1 RX)
ESP32-S3 (GPIO16) ◄─RX──  STM32 PA9  (USART1 TX)
ESP32-S3 (GND)   ─────── STM32 GND
```

> Chi tiết xem [pinout.md](pinout.md).

### 3.3 Memory map STM32F103 (target: STM32F103C8T6, 128 KB)

```
0x0800_0000  ┌─────────────────┐
             │   Bootloader    │  16 KB  (cố định; verify + VTOR jump)
0x0800_4000  ├─────────────────┤
             │  Application A  │  52 KB  (firmware đang chạy)
0x0801_1000  ├─────────────────┤
             │  Application B  │  52 KB  (OTA staging slot)
0x0801_E000  ├─────────────────┤
             │  Metadata Bank0 │  4 KB   (ping-pong A)
0x0801_F000  ├─────────────────┤
             │  Metadata Bank1 │  4 KB   (ping-pong B)
0x0802_0000  └─────────────────┘
```

Layout chọn **equal A/B 52 KB** + **2×4 KB ping-pong metadata**: cần cho swap A↔B (slot phải
bằng nhau) và power-fail safety. Page size = 1 KB khớp `chunk_size` trong `ota_manifest_t`.
Tổng 16 + 52 + 52 + 4 + 4 = 128 KB khớp đúng dung lượng flash. Đồng bộ với
[checklist §3A](checklist.md), [initial_ideas.md](initial_ideas.md) và
[flash_map.md](../../3_node_stm32/docs/flash_map.md).

---

## 4. Giao thức UART (common/protocol_packet.h)

### 4.1 Frame format

```
┌──────────┬──────────┬───────┬──────────┬────────────────┬───────────────────┬─────────┬─────────┐
│ START    │ PKT_TYPE │ FLAGS │ SEQ_NUM  │ PAYLOAD_LENGTH │ PAYLOAD[0..N]     │ CRC16   │ END     │
│ 0x7E     │ 1 byte   │1 byte │ 1 byte   │ 2 bytes (LE)   │ max 1024 bytes    │ 2 bytes │ 0x7F    │
└──────────┴──────────┴───────┴──────────┴────────────────┴───────────────────┴─────────┴─────────┘
```

Byte stuffing: `0x7E`, `0x7F`, `0x7D` trong payload được escape bằng `0x7D ^ 0x20`.

### 4.2 Packet types

| Hex | Tên | Hướng | Mô tả |
|---|---|---|---|
| `0x01` | `PKT_TYPE_HELLO` | GW→Node | Khởi động session |
| `0x02` | `PKT_TYPE_CHALLENGE` | Node→GW | 32-byte random nonce |
| `0x03` | `PKT_TYPE_RESPONSE` | GW→Node | ASCON-128a MAC của nonce |
| `0x04` | `PKT_TYPE_SESSION_KEY` | Node→GW | X25519 ephemeral pubkey |
| `0x10` | `PKT_TYPE_MANIFEST` | GW→Node | `ota_manifest_t` (212 bytes) |
| `0x11` | `PKT_TYPE_FW_CHUNK` | GW→Node | Encrypted firmware chunk |
| `0x12` | `PKT_TYPE_FW_VERIFY` | bidirectional | Hash verify request/result |
| `0x13` | `PKT_TYPE_FW_COMMIT` | GW→Node | Lệnh commit và reboot |

---

## 5. OTA Manifest (common/manifest_def.h)

```c
typedef struct {
    /* Header — 8 bytes */
    uint32_t magic;            // 0x4F54414D ("MOTA")
    uint8_t  version_major;    // 1
    uint8_t  version_minor;    // 0
    uint16_t header_size;

    /* Device — 10 bytes */
    uint8_t  vendor_id[4];
    uint8_t  device_class[2];
    uint32_t device_id;

    /* Firmware — 16 bytes */
    uint32_t fw_version;
    uint32_t fw_size;
    uint32_t fw_entry_point;
    uint16_t chunk_size;       // default 1024 bytes
    uint16_t total_chunks;

    /* Anti-rollback — 8 bytes */
    uint32_t security_version; // phải >= version trong metadata flash
    uint32_t build_timestamp;

    /* Crypto — 48 bytes */
    uint8_t  fw_hash[32];      // ASCON-Hash256 của toàn bộ firmware plaintext
    uint8_t  nonce_base[16];   // base nonce; chunk i dùng nonce_base XOR i

    /* Signature — 64 bytes (CUỐI CÙNG, không nằm trong vùng ký) */
    uint8_t  signature[64];    // Ed25519 sign của 148 bytes đầu
} ota_manifest_t;              // Tổng: 212 bytes
```

`MANIFEST_SIGNED_SIZE = sizeof(ota_manifest_t) - 64 = 148 bytes`

---

## 6. Mô hình bảo mật

### 6.1 Threat model

| Mối đe dọa | Biện pháp đối phó |
|---|---|
| Firmware giả mạo | Ed25519 signature trên manifest |
| Firmware bị sửa đổi khi truyền | ASCON-128a AEAD tag mỗi chunk |
| Node giả mạo (replay/impersonation) | CRA với ASCON-128a MAC + ephemeral nonce |
| Downgrade firmware cũ | Anti-rollback `security_version` trong metadata flash |
| Session replay | X25519 ephemeral key exchange (mỗi session dùng key mới) |
| Eavesdropping UART | ASCON-128a chunk encryption |

### 6.2 Luồng CRA chi tiết

```
Node sinh nonce N (32 bytes random)
  → gửi PKT_CHALLENGE(N)
Gateway nhận N, dùng shared_secret K để tính:
  MAC = ASCON-128a-MAC(K, N)
  → gửi PKT_RESPONSE(MAC)
Node tính lại MAC' = ASCON-128a-MAC(K, N)
  → so sánh MAC == MAC'
  → nếu khớp: xác thực thành công
```

### 6.3 Mã hóa chunk

```
Cho chunk thứ i:
  nonce_i     = nonce_base XOR (uint128) i
  session_key = ASCON-XOF128(shared_secret || salt || "ota-chunk-key-v1")
  ciphertext_i, tag_i = ASCON-128a-AEAD-Enc(session_key, nonce_i,
                                            plaintext_i, AD = chunk_idx)
```

**Primitive unification:** toàn bộ pipeline chỉ cần ASCON permutation (ASCON-p).
ASCON-128a cho AEAD, ASCON-XOF128 cho KDF, ASCON-Hash256 cho firmware hash.
Không kéo SHA-256 / HKDF vào STM32 — tiết kiệm ROM và đồng nhất luận điểm "ASCON-CRA".
Ed25519 + X25519 (qua uECC) vẫn dùng cho chữ ký và ECDHE vì chưa có primitive ASCON
thay thế tương đương.

---

## 7. Stack phần mềm

### 7.1 Server (Python 3)

| File | Chức năng |
|---|---|
| `gui_app.py` | Tkinter GUI: tab Key Management, Manifest, Packaging |
| `src/crypto_utils.py` | ASCON-128a, X25519, Ed25519, HKDF |
| `src/manifest_builder.py` | Tạo và ký `ota_manifest_t` |
| `src/packet_builder.py` | Chunk firmware, ASCON-128a encrypt |

**Dependencies:** `cryptography`, `pyascon`, `httpx`, `websockets`, `pyserial`, `pydantic`, `rich`

### 7.2 Gateway (ESP32 — ESP-IDF + PlatformIO)

| File | Chức năng |
|---|---|
| `main/main.c` | Entry point: WiFi init, UART bridge task, OTA manager |
| `main/uart_bridge.*` | UART send/receive với STM32 |
| `main/protocol_parser.*` | Frame parser, CRC16 verify |
| `main/ota_cache.*` | Cache firmware chunks (RAM-based scaffold) |

**Build:** `pio run -e esp32dev` hoặc ESP-IDF `idf.py build`

### 7.3 Node (STM32 — PlatformIO + STM32Cube HAL)

| File | Chức năng |
|---|---|
| `src/main.c` | App entry: System_Init + ota_handler_init + main loop |
| `src/ota_handler.*` | OTA state machine (9 trạng thái) |
| `src/crypto_port.*` | Port ASCON, Ed25519, X25519 cho STM32 [⚠ có TODOs] |
| `src/flash_driver.*` | Flash erase/write/read cho OTA slot |
| `src/system_init.*` | Clock 72MHz, USART1, GPIO |
| `src/aead.c` | ASCON-128a AEAD implementation |
| `src/permutations.c` | ASCON-p permutation |
| `lib/uECC.h` | ECC library cho X25519/Ed25519 |

**Build:** `pio run -e bluepill_f103c8`

---

## 8. Thiết kế thí nghiệm

### TN1 — Luồng OTA end-to-end (Correctness)

| | |
|---|---|
| **Mục tiêu** | Xác nhận toàn bộ pipeline hoạt động đúng |
| **Input** | Firmware v1 (LED 1Hz) → OTA lên v2 (LED 4Hz) |
| **Đo** | Tổng thời gian, số packet, log UART |
| **Pass** | LED chớp đúng tần số mới sau reboot |

### TN2 — Anti-Rollback

| | |
|---|---|
| **Mục tiêu** | Hệ thống từ chối firmware security_version thấp hơn |
| **Input** | Node đang chạy version=2, thử OTA version=1 |
| **Đo** | Error code `OTA_ERR_VERSION_ROLLBACK (0x80)` |
| **Pass** | Node không reboot, flash slot B không bị ghi |

### TN3 — Phát hiện firmware bị tamper

| | |
|---|---|
| **Mục tiêu** | Chunk bị sửa 1 byte phải bị từ chối |
| **Input** | Flip 1 byte trong encrypted chunk bằng hex editor |
| **Đo** | Error code `OTA_ERR_MAC_VERIFY_FAILED (0x43)`, chunk index lỗi |
| **Pass** | Session hủy, flash không bị ghi, Node tiếp tục chạy |

### TN4 — Benchmark hiệu năng crypto trên STM32

**Phương pháp đo:** GPIO toggle + Logic Analyzer (chính xác ~42ns @ 24MHz)

```c
// Trong crypto_port.c
HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET);
crypto_operation(...);
HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);
// Logic Analyzer đo pulse width = thời gian thực thi
```

| Operation | Input size | Kỳ vọng (72MHz M3) |
|---|---|---|
| ASCON-128a encrypt | 1 KB chunk | 5–15 ms |
| ASCON-128a decrypt | 1 KB chunk | 5–15 ms |
| ASCON-128a MAC (CRA) | 32 bytes | < 1 ms |
| Ed25519 verify (manifest) | 148 bytes + sig | **500ms–2s** |
| X25519 derive | 32-byte scalar | 300ms–1s |
| SHA-256 hash | 48 KB firmware | 50–200 ms |
| Flash write | 1 KB page | ~5 ms |

**Tổng thời gian OTA ước tính (48KB firmware, chunk=1KB):**
```
T_total = T_handshake + T_Ed25519 + 48 × (T_ascon_decrypt + T_flash_write)
        ≈ (T_X25519 + T_MAC) + T_Ed25519 + 48 × (10ms + 5ms)
        ≈ ~1s + ~1s + ~720ms ≈ 2.5–4s
```

### TN5 — Tài nguyên Flash/RAM

```bash
pio run -e bluepill_f103c8
# Mục tiêu:
# Flash (Bootloader): < 12 KB / 16 KB
# Flash (Application): < 45 KB / 48 KB
# RAM peak: < 15 KB / 20 KB
```

---

## 9. Trạng thái triển khai

**Phase tags** (cam kết phạm vi): `Q2` = MVP demo end-to-end; `Q3` = hardening; `Q4` = production multi-node.

### 9.1 Q2 scope (ĐÓNG BĂNG — tất cả mục này phải đạt để demo)

| Module | Trạng thái | Ghi chú |
|---|---|---|
| Server `crypto_utils.py` (ASCON-128a, X25519, Ed25519) | ✅ Done | Dùng `cryptography` + `pyascon` |
| Server `crypto_utils.py`: chuyển HKDF → **ASCON-XOF128** (primitive unification) | ⚠ Migrate | `pyascon` có sẵn ASCON-XOF; thay HKDF wrapper |
| Server `crypto_utils.py`: chuyển SHA-256 → **ASCON-Hash256** cho `fw_hash[32]` | ⚠ Migrate | `pyascon` có sẵn ASCON-Hash256 |
| Server `manifest_builder.py` (binary `ota_manifest_t` 212 B, Ed25519 sign) | ✅ Done | |
| Server `packet_builder.py` (chunk 1 KB + ASCON-128a encrypt) | ✅ Done | |
| Server GUI (key gen / manifest / package / connection) | ✅ Done | MVC `src/gui/` |
| Gateway `uart_bridge.*` (UART TX/RX + framing/CRC16) | ✅ Scaffold | |
| Gateway OTA relay (main.c: TCP/HTTP in, UART out, state-driven) | ❌ TODO | **Q2 blocker** |
| Gateway `ota_cache` (RAM stub đủ cho 52 KB firmware) | ⚠ Stub → RAM-OK | RAM 512 KB dư; không cần PSRAM Q2 |
| Node `ota_handler.c` transport integration | ⚠ Partial | State machine có; nối packet dispatch ↔ crypto_port |
| Node `crypto_port.c`: Ed25519 verify qua uECC | ❌ TODO | **Q2 blocker** |
| Node `crypto_port.c`: X25519 derive qua uECC | ❌ TODO | **Q2 blocker** |
| Node `crypto_port.c`: **ASCON-XOF128 KDF** (reuse `permutations.c`) | ❌ TODO | **Q2 blocker** — primitive unification, thay HKDF |
| Node `crypto_port.c`: **ASCON-Hash256** (reuse `permutations.c`) | ❌ TODO | **Q2 blocker** — thay SHA-256; khớp `fw_hash[32]` |
| Node `aead.c` + `permutations.c` (ASCON-128a AEAD + ASCON-p) | ✅ Done | Base cho XOF/Hash256 reuse |
| Node `flash_driver.c` (erase/write/read slot B) | ✅ Scaffold | |
| Bootloader: metadata đọc + chọn active slot + VTOR set + jump | ❌ TODO | **Q2 blocker** |
| Bootloader: Ed25519 verify **manifest** (chưa cần full-image) | ❌ TODO | Q2 đủ với verify manifest |
| Anti-rollback: `security_counter` persist vào metadata | ❌ TODO | **Q2 blocker** — phục vụ TN2 |
| Demo payload trên OLED (SSD1306 I2C1, PB6/PB7) | ❌ TODO | Q2 — giá trị demo cao |

### 9.2 Q3 (hardening — sau khi Q2 demo OK)

- Constant-time tag compare + `secure_zeroize` audit toàn bộ crypto path.
- Entropy trên STM32: ADC floating noise + Timer jitter + RCT/APT (bù TRNG thiếu).
- Ping-pong metadata 2 × 4 KB với seq counter + CRC32 nguyên tử.
- Power-fail recovery (pending-flag 2-phase commit).
- Bootloader full-image Ed25519 verify (phủ toàn slot sau decrypt).
- RDP Level 1 + WRP cho vùng Bootloader.
- Hierarchical Key Management: K_anchor → DMK → K_session.
- Static K_FW + wrap bằng K_session (hiện Q2 server truyền key trực tiếp qua session).
- Server ký thêm handshake payload chống MITM từ Gateway.

### 9.3 Q4 (production)

- CBOR deterministic (RFC 8949) cho manifest, kèm parser + fuzzer 100 k inputs.
- Chuyển Gateway sang MQTT + TLS + certificate pinning.
- Multi-node fleet management trên server.
- Cân nhắc RDP Level 2 (one-way — chỉ làm sau khi toolchain hoàn toàn ổn định).

---

## 10. Vấn đề đã biết & cần giải quyết (Q2 focus)

**Phần cứng đã chốt:** ESP32-S3 N16R8 + STM32F103C8T6 (128 KB) + OLED SSD1306. Layout
flash 16/52/52/8 (16 KB Boot + 52 KB Slot A + 52 KB Slot B + 8 KB Metadata 2-bank).

| # | Vấn đề | Phase | Ảnh hưởng |
|---|---|---|---|
| 1 | `2_gateway_esp32/platformio.ini` đang `esp32dev`, phải đổi sang `esp32-s3-devkitc-1` cho khớp phần cứng đã chốt | **Q2** | Build target khớp ESP32-S3 N16R8 |
| 2 | `crypto_port.c` placeholder Ed25519 verify + X25519 derive | **Q2** | Blocker TN1/TN2/TN3 |
| 3 | `crypto_port.c` thiếu ASCON-XOF128 KDF + ASCON-Hash256 (reuse `permutations.c`) | **Q2** | Primitive unification — luận điểm cốt lõi của đồ án |
| 4 | `crypto_utils.py` đang HKDF/SHA-256, migrate sang `pyascon.ascon_xof128` + `ascon_hash256` | **Q2** | Đồng bộ với node |
| 5 | Gateway OTA relay (main.c): WiFi STA + TCP pull + UART relay state-driven | **Q2** | Blocker TN1 |
| 6 | Bootloader: đọc Bank 0, verify CRC + Ed25519 manifest, set VTOR, jump | **Q2** | Blocker boot path |
| 7 | Anti-rollback `security_counter` persist vào flash metadata | **Q2** | Blocker TN2 |
| 8 | `common/boot_metadata.h` chưa tồn tại (bootloader + app cần cùng header) | **Q2** | Tạo mới |
| 9 | Linker `STM32F103_App.ld` + `STM32F103_Boot.ld` cập nhật MEMORY 16/52/52/8 | **Q2** | Khớp flash_map.md mới |
| 10 | OLED display driver + screen state (SSD1306 I²C1 PB6/PB7) + 2 bitmap demo v1/v2 | **Q2** | Minh chứng OTA trực quan |
| 11 | AD trong AEAD: gán `chunk_idx ‖ device_class ‖ fw_version` mỗi chunk | **Q2** | Bind chunk vào ngữ cảnh chống reorder/rollback |
| 12 | Constant-time tag compare + `secure_zeroize` audit toàn bộ crypto path | Q3 | Chống timing attack + DSE |
| 13 | Entropy ADC + Timer jitter + RCT/APT | Q3 | Bù thiếu TRNG; Q2 dùng nonce-from-server |
| 14 | Ping-pong metadata 2×4 KB atomic + power-fail recovery | Q3 | Layout đã dành chỗ Bank 1 |
| 15 | Full-image ASCON-Hash256 verify trong bootloader (sau decrypt + reassemble) | Q3 | Q2 chỉ verify manifest |
| 16 | RDP Level 1 + WRP vùng bootloader | Q3 | Không đụng RDP2 ở Q2/Q3 |
| 17 | K_FW static + wrap bằng K_session | Q3 | Q2 server truyền key qua phiên trực tiếp |
| 18 | HKM (K_anchor → DMK → K_session), per-device anchor | Q3 | Multi-node future |
| 19 | Server ký bổ sung handshake payload chống MITM từ Gateway | Q3 | Lớp phòng thủ thêm |
| 20 | CBOR deterministic manifest + parser fuzzer | Q4 | Thay binary packed |
| 21 | Gateway MQTT + TLS + certificate pinning thay HTTP/TCP | Q4 | Production fleet |
| 22 | Multi-node fleet management trên server | Q4 | Sau Q3 HKM |

---

## 11. Thứ tự triển khai — ràng buộc Q2

**Q2 phải đạt được trước tất cả việc khác.** Các sprint dưới đây chỉ phục vụ Q2.

```
Sprint Q2.1 — Unblock build + chốt platform (phần cứng đã chốt)
  □ Đổi 2_gateway_esp32/platformio.ini: board → esp32-s3-devkitc-1, framework giữ
    espidf hoặc arduino tuỳ team; verify build pass
  □ Cập nhật STM32F103_App.ld + STM32F103_Boot.ld: MEMORY layout 16/52/52/8
    (xem flash_map.md)
  □ Tạo header common/boot_metadata.h (dùng chung bootloader + application)

Sprint Q2.2 — STM32 crypto_port + transport (unblock TN1, TN3)
  □ crypto_port.c: Ed25519 verify manifest qua uECC
  □ crypto_port.c: X25519 derive qua uECC
  □ crypto_port.c: ASCON-XOF128 KDF (reuse permutations.c — KHÔNG dùng HKDF)
  □ crypto_port.c: ASCON-Hash256 cho fw_hash (reuse permutations.c — KHÔNG dùng SHA-256)
  □ Server: migrate crypto_utils.py HKDF → ASCON-XOF, SHA-256 → ASCON-Hash256
    (pyascon đã có sẵn cả hai — chỉ thay wrapper)
  □ ota_handler.c: nối packet dispatch ↔ crypto_port ↔ flash_driver
  □ Audit: constant-time tag compare + secure_zeroize cho session key

Sprint Q2.3 — Gateway OTA relay (unblock TN1)
  □ main.c: WiFi STA + HTTP/TCP pull firmware từ Python server
  □ main.c: state-driven relay sang UART (HELLO→CHALLENGE→RESPONSE→
    SESSION_KEY→MANIFEST→CHUNK[]→VERIFY→COMMIT)
  □ Chờ ACK từng chunk trước khi gửi chunk kế; timeout + retry tối thiểu

Sprint Q2.4 — Bootloader (unblock TN2, boot-safe)
  □ Đọc metadata Bank0, verify CRC32
  □ Chọn active_slot; set SCB->VTOR; jump (disable IRQ + SysTick trước jump)
  □ Anti-rollback: so sánh manifest.security_version với metadata
  □ Persist security_counter sau khi boot OK

Sprint Q2.5 — Demo payload + OLED (làm nổi bật kết quả OTA)
  □ display_driver.c/h (SSD1306 I2C1, PB6=SCK, PB7=SDA)
  □ display_screens.c/h: IDLE/AUTH/DOWNLOAD/VERIFY/COMMIT/ERROR + demo
  □ display_set_state() hook trong ota_handler
  □ 2 bitmap demo khác nhau giữa firmware v1 và v2

Sprint Q2.6 — Experiments + báo cáo
  □ TN1 (happy path end-to-end) → pass
  □ TN2 (anti-rollback) → pass
  □ TN3 (chunk tamper → MAC fail) → pass
  □ TN4 (benchmark crypto timing qua GPIO + Logic Analyzer)
  □ TN5 (ROM/RAM footprint từ .map)
```

Sau khi Q2 đạt: xem [§9.2 Q3](#9-trạng-thái-triển-khai) và [§9.3 Q4](#9-trạng-thái-triển-khai).

---

## 12. Tài liệu tham khảo

- NIST SP 800-232: ASCON Lightweight Cryptography Standard (2023)
- RFC 8032: Edwards-Curve Digital Signature Algorithm (Ed25519)
- RFC 7748: Elliptic Curves for Diffie-Hellman Key Agreement (X25519)
- STM32F103C8 Reference Manual (RM0008)
- ESP32-S3 Technical Reference Manual
- [pinout.md](pinout.md) — Sơ đồ chân và kết nối phần cứng
- [hw_used.md](hw_used.md) — Danh sách linh kiện
