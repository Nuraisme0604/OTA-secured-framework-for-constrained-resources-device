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
┌──────────────────────────────────────────────────────────────────────┐
│                         OTA Pipeline                                  │
│                                                                        │
│  ┌─────────────┐    WiFi/TCP     ┌─────────────┐    UART 115200      │
│  │   Server    │ ─────────────► │  Gateway    │ ──────────────────► │
│  │  (Python)   │ ◄───────────── │  (ESP32-S3) │ ◄────────────────── │
│  └─────────────┘                └─────────────┘                      │
│         │                              │                   ┌──────────┐│
│    GUI + crypto                  WiFi STA +           │  Node    ││
│    manifest sign                 UART bridge          │ (STM32)  ││
│    chunk encrypt                 OTA cache            └──────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 2.1 Thành phần

| Thành phần | Phần cứng | Thư mục | Vai trò |
|---|---|---|---|
| Server | PC (host) | `1_server_python/` | Tạo key, ký manifest, mã hóa firmware, GUI |
| Gateway | ESP32-S3 N16R8 | `2_gateway_esp32/` | Cầu nối WiFi↔UART, relay OTA session |
| Node | STM32F103C8T6 | `3_node_stm32/` | Nhận, xác thực, giải mã, ghi flash, boot |

### 2.2 Luồng OTA tổng quát

```
Server                    Gateway                    Node
  │                          │                         │
  │── POST /ota/start ──────►│                         │
  │                          │── PKT_HELLO ───────────►│
  │                          │◄── PKT_CHALLENGE ────────│  (32-byte nonce)
  │                          │── PKT_RESPONSE ─────────►│  (ASCON-128a MAC)
  │                          │◄── PKT_SESSION_KEY ──────│  (X25519 pubkey)
  │                          │── PKT_MANIFEST ─────────►│  (ota_manifest_t)
  │                          │◄── ACK ──────────────────│  (Ed25519 verify OK)
  │                          │── PKT_FW_CHUNK[0..N] ───►│  (ASCON-128a encrypted)
  │                          │◄── ACK[i] ───────────────│  (per chunk)
  │                          │── PKT_FW_VERIFY ────────►│
  │                          │◄── PKT_FW_VERIFY(result)─│  (SHA-256 check)
  │                          │── PKT_FW_COMMIT ─────────►│
  │                          │                         │── reboot → bootloader
  │                          │                         │── validate slot B
  │                          │                         │── swap A↔B → run
```

---

## 3. Phần cứng

### 3.1 Danh sách linh kiện

| Thiết bị | Thông số | Vai trò |
|---|---|---|
| ESP32-S3 N16R8 | 240MHz dual-core, 16MB Flash, 8MB PSRAM, WiFi 2.4GHz BLE5 | Gateway |
| STM32F103C8T6 Blue Pill | 72MHz Cortex-M3, 128KB Flash, 20KB SRAM | OTA Node |
| OLED 0.96" SSD1306 | 128×64, I2C, 3.3V–5V | Hiển thị trạng thái (tùy chọn) |
| Logic Analyzer 8ch | 24MHz max, 1.8V–5.5V, USB | Đo UART timing |
| ST-Link Mini V2 | SWD | Nạp/debug STM32 |
| CP2102 / CH340 | USB-Serial | Debug UART (tuỳ chọn) |

### 3.2 Kết nối phần cứng

```
ESP32-S3 (GPIO17) ──TX──► STM32 PA10 (USART1 RX)
ESP32-S3 (GPIO16) ◄─RX──  STM32 PA9  (USART1 TX)
ESP32-S3 (GND)   ─────── STM32 GND
```

> Chi tiết xem [pinout.md](pinout.md).

### 3.3 Memory map STM32F103

```
0x0800_0000  ┌─────────────────┐
             │   Bootloader    │  16 KB  (nạp cố định, không OTA)
0x0800_4000  ├─────────────────┤
             │  Application A  │  ~48 KB (firmware đang chạy)
0x0801_0000  ├─────────────────┤
             │  Application B  │  ~48 KB (OTA staging slot)
0x0801_FC00  ├─────────────────┤
             │  Metadata/Flags │  1 KB   (boot state, security version)
0x0802_0000  └─────────────────┘
```

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
    uint8_t  fw_hash[32];      // SHA-256 toàn bộ firmware sau decrypt
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
  nonce_i  = nonce_base XOR (uint128) i
  session_key = HKDF(shared_secret, "ota-chunk-key")
  ciphertext_i, tag_i = ASCON-128a-AEAD-Enc(session_key, nonce_i, plaintext_i)
```

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

| Module | Trạng thái | Ghi chú |
|---|---|---|
| Server crypto_utils.py | ✅ Hoàn chỉnh | ASCON, Ed25519, X25519, HKDF |
| Server manifest_builder.py | ✅ Hoàn chỉnh | Aligned với manifest_def.h |
| Server packet_builder.py | ✅ Hoàn chỉnh | Chunk + ASCON encrypt |
| Server GUI | ✅ Hoàn chỉnh | 3 tab workflow |
| Gateway uart_bridge | ✅ Scaffold | UART TX/RX OK |
| Gateway protocol_parser | ✅ Scaffold | Frame + CRC16 |
| Gateway ota_cache | ⚠️ Stub | RAM-only, chưa đủ cho 48KB |
| Gateway OTA manager (main.c) | ❌ TODO | Luồng relay chưa implement |
| Node ota_handler | ⚠️ Partial | State machine có, transport TODO |
| Node crypto_port | ⚠️ Placeholder | Ed25519/X25519 chưa production-safe |
| Node flash_driver | ✅ Scaffold | Erase/write/read có |
| Node ASCON (aead.c) | ✅ Hoàn chỉnh | Native C implementation |
| Bootloader | ❌ TODO | Framework có, verify/rollback chưa làm |

---

## 10. Vấn đề đã biết & cần giải quyết

| # | Vấn đề | Ưu tiên | Ảnh hưởng |
|---|---|---|---|
| 1 | `hw_used.md` ghi ESP32-S3 nhưng code dùng `esp32dev` (ESP32 thường) | Cao | Build sai target |
| 2 | `crypto_port.c` placeholder cho Ed25519 verify, X25519 | Cao | TN2, TN3, TN4 bị block |
| 3 | Gateway OTA manager chưa implement | Cao | TN1 bị block |
| 4 | Bootloader signature verify chưa làm | Trung | Boot path không an toàn |
| 5 | `ota_cache` chỉ là RAM stub (8MB PSRAM của S3 chưa dùng) | Trung | Giới hạn firmware size |
| 6 | Anti-rollback metadata chưa persist vào flash | Trung | TN2 cần kiểm tra |

---

## 11. Thứ tự triển khai đề xuất

```
Sprint 1 (unblock build):
  □ Đồng bộ board target: esp32dev → esp32s3 trong platformio.ini
  □ Verify build pass cả 3 component

Sprint 2 (unblock TN1 - happy path):
  □ Implement Gateway OTA manager flow trong main.c
  □ Hoàn thiện Node transport integration trong ota_handler.c

Sprint 3 (unblock TN2, TN3 - security):
  □ Implement Ed25519 verify trong crypto_port.c (dùng uECC)
  □ Implement X25519 derive trong crypto_port.c
  □ Implement anti-rollback metadata persist vào flash

Sprint 4 (TN4 - benchmark):
  □ Thêm GPIO timing instrumentation vào crypto_port.c
  □ Chạy đo đạc với Logic Analyzer
  □ Thu thập số liệu cho bài báo

Sprint 5 (hoàn thiện):
  □ Bootloader signature verify + rollback logic
  □ ota_cache dùng PSRAM (nếu dùng ESP32-S3)
  □ OLED status display (tùy chọn cho demo)
```

---

## 12. Tài liệu tham khảo

- NIST SP 800-232: ASCON Lightweight Cryptography Standard (2023)
- RFC 8032: Edwards-Curve Digital Signature Algorithm (Ed25519)
- RFC 7748: Elliptic Curves for Diffie-Hellman Key Agreement (X25519)
- STM32F103C8 Reference Manual (RM0008)
- ESP32-S3 Technical Reference Manual
- [pinout.md](pinout.md) — Sơ đồ chân và kết nối phần cứng
- [hw_used.md](hw_used.md) — Danh sách linh kiện
