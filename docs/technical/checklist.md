Dưới góc độ kiến trúc hệ thống E2E (End-to-End) và an toàn thông tin, hệ thống OTA của bạn được phân tách thành 3 miền rõ rệt: **Server (Root Authority)**, **ESP32-S3 (Edge Gateway)**, và **STM32F103 (End Node)**. Mỗi thiết bị đảm nhận một vai trò cụ thể trong mô hình đe dọa (Threat Model) và ngân sách tài nguyên.

Dưới đây là bộ checklist kỹ thuật và bảo mật chuyên sâu, được thiết kế riêng cho từng thực thể trong hệ thống ASCON-CRA:

> **Phase tags:** `(Q2)` = MVP demo-able end-to-end (đây là cam kết bắt buộc); `(Q3)` = Hardening (RDP/WRP, CBOR canonical, DMK, constant-time audit); `(Q4)` = Field trial multi-node + production server. Không đánh tag = nền tảng, bắt buộc từ Q2.

> **Q2 non-negotiable primitives (primitive unification theo luận điểm ASCON-CRA):** ASCON-128a AEAD, **ASCON-XOF128 làm KDF** (không dùng HKDF), **ASCON-Hash256 làm firmware hash** (không dùng SHA-256). Ed25519 + X25519 (qua uECC) vẫn dùng vì chưa có primitive ASCON thay thế tương đương. Code Python hiện đang wire HKDF/SHA-256 — phải migrate qua `pyascon` cho Q2.

### 1. Checklist cho Server (Root Authority - Máy chủ Cấp phát)
Máy chủ là nơi tin cậy tuyệt đối, chịu trách nhiệm sinh khóa, đóng gói và ký số.

**A. Đóng gói & Mã hóa Firmware (Packaging & Encryption)**
*   [ ] **(Q3)** Sinh ngẫu nhiên Khóa nội dung tĩnh ($K_{FW}$) 16 bytes và $Nonce_{Base}$ 16 bytes cho mỗi bản build firmware. **(Q2)** hiện `packet_builder.py` nhận `key` truyền trực tiếp qua phiên (chưa tách $K_{FW}$ / $K_{Session}$).
*   [ ] **(Q2)** Phân mảnh (Chunking) firmware thành các khối 1024 bytes (khớp với kích thước Page của Flash STM32). ✅ `packet_builder.py` đã làm.
*   [ ] **(Q2)** Mã hóa từng khối bằng ASCON-128a với $Nonce_i = Nonce_{Base} \oplus i$. ✅ đã làm.
*   [ ] **(Q2)** Đính kèm Associated Data (AD) vào ASCON-128a chứa `chunk_idx || device_class || fw_version` để bind chunk vào ngữ cảnh (chống rollback + reorder ngay lớp mật mã). ⚠ code chưa có AD — cần bổ sung trong `packet_builder.py` và đồng bộ phía node.

**B. Quản lý Manifest & Chữ ký số**
*   [ ] **(Q2)** Tạo Manifest chứa: Version, Kích thước Firmware, **ASCON-Hash256** của toàn bộ plaintext firmware, $Nonce_{Base}$, Salt cho KDF. ⚠ `crypto_utils.py` hiện dùng SHA-256 — migrate qua `pyascon.ascon_hash256`.
*   [ ] **(Q2)** Chuẩn hóa Manifest về định dạng nhị phân cố định (`ota_manifest_t` trong `common/manifest_def.h`, little-endian, packed) để đảm bảo tính tất định trước khi ký. ✅ đã có. **(Q3)** Chuyển sang Canonical CBOR (RFC 8949 §4.2.1 Core Deterministic Encoding); bump `MANIFEST_VERSION` và cập nhật đồng bộ cả 3 thành phần (server builder + node parser + gateway relay).
*   [ ] **(Q2)** Dùng khóa riêng Ed25519 để ký lên toàn bộ chuỗi byte của Manifest (trừ trường chứa chữ ký). ✅ đã làm.

**C. Handshake & Bảo mật Chuyển tiếp (Forward Secrecy)**
*   [ ] **(Q2)** Sinh cặp khóa tạm thời (ephemeral keys) X25519 ($sk_{srv}, pk_{srv}$) cho mỗi phiên cập nhật của thiết bị.
*   [ ] **(Q2)** Tính toán Shared Secret (SS) và dẫn xuất Khóa phiên ($K_{Session}$) bằng **ASCON-XOF128**: $K_{sess} = ASCON\text{-}XOF128(SS \| salt \| \text{"OTA\_Transport\_v1"})$. ⚠ `crypto_utils.py` hiện dùng HKDF — migrate qua `pyascon.ascon_xof128`. KHÔNG fallback HKDF cho Q2.
*   [ ] **(Q3)** "Gói" (Key Wrap) khóa $K_{FW}$ bằng $K_{Session}$ sử dụng ASCON-128a (chỉ áp dụng sau khi tách $K_{FW}$ ở §A).
*   [ ] **(Q3)** Ký số lên Payload Handshake ($pk_{srv} || Wrapped\_K$) để thiết bị STM32 chống lại tấn công MITM từ chính ESP32 Gateway.
*   [ ] **(Q3)** Triển khai Hierarchical Key Management: server lưu $K_{anchor}$ 32 B riêng cho từng node (not shared). Derive Device Master Key per-device: $DMK = ASCON\text{-}XOF128(K_{anchor} \| device\_id \| \text{"DMK\_v1"})$. Mất 1 anchor không ảnh hưởng các node còn lại trong fleet.

---

### 2. Checklist cho ESP32-S3 N16R8 (Edge Gateway - Cổng Biên)
ESP32-S3 N16R8 hoạt động như Proxy + Cache. Tài nguyên lớn (240 MHz dual-core, 16 MB Flash, 8 MB PSRAM, WiFi 2.4 GHz, BLE5) nhưng **không được tin cậy** để giữ khóa bí mật của STM32 — node tự xác thực qua Ed25519 manifest + ECDHE end-to-end với Server.

**A. Giao tiếp Mạng & Bộ nhớ đệm (Networking & Caching)**
*   [ ] **(Q2)** Thiết lập kết nối HTTP trong LAN tới Server Python (SSID WiFi hardcode chấp nhận được cho demo) để pull manifest + ciphertext chunks. **(Q4)** Chuyển sang MQTT broker (Mosquitto) hoặc HTTPS + token auth + certificate pinning cho fleet deployment thực.
*   [ ] **(Q2)** Cập nhật `2_gateway_esp32/platformio.ini`: `board = esp32-s3-devkitc-1` (phần cứng đã chốt = ESP32-S3 N16R8). Pin UART: GPIO 17 = TX (→ STM32 PA10), GPIO 18 = RX (← STM32 PA9), tránh GPIO 26–37 do octal flash + PSRAM N16R8 chiếm dụng.
*   [ ] **(Q2)** Cache firmware + manifest trong DRAM ESP32-S3 (52 KB vừa, 512 KB SRAM dư). **(Q3)** Tận dụng PSRAM 8 MB cho fleet hoặc firmware lớn hơn 100 KB.
*   [ ] **(Q2)** Tính CRC32 độc lập của file tải về (bỏ MD5 — lỗi thời, không thêm giá trị so với CRC32 ở tầng này).

**B. Xử lý Giao thức Proxy (Bridge Logic)**
*   [ ] **(Q2)** Hoạt động như "Transparent Proxy" trong pha handshake ECDHE. Chuyển tiếp nguyên vẹn `PKT_SESSION_KEY` từ STM32 lên Server và pubkey Server xuống STM32. Tuyệt đối không can thiệp vào tham số mật mã.
*   [ ] **(Q2)** Triển khai FSM relay UART với STM32 (mirror 8 packet types trong `common/protocol_packet.h`).
*   [ ] **(Q2)** Streaming chunk: chờ ACK từ STM32 sau khi ghi Flash thành công thì mới truyền chunk tiếp. Xử lý timeout + retry tối thiểu.

---

### 3. Checklist cho STM32F103C8T6 (End Node - Nút Đích)
Phần cứng: Blue Pill 72 MHz Cortex-M3, **128 KB Flash**, 20 KB SRAM. Đây là môi trường khắc nghiệt nhất — yêu cầu tối ưu ROM/RAM cực hạn và phòng thủ vật lý. Có gắn thêm **OLED 0.96" SSD1306** trên I²C1 (PB6 SCK / PB7 SDA) làm demo payload.

**A. Cấu trúc Flash & Bootloader (Resilience)**
*   [ ] **(Q2)** Cấu hình Flash Map (STM32F103C8T6 — 128 KB): 16 KB Bootloader + 52 KB Slot A + 52 KB Slot B + 8 KB Metadata region (Bank 0 dùng Q2, Bank 1 ping-pong Q3). Page size 1 KB khớp chunk size. Cập nhật linker `STM32F103_App.ld` + `STM32F103_Boot.ld`.
*   [ ] **(Q2)** Tạo header `common/boot_metadata.h` dùng chung giữa bootloader + application (magic + active/pending slot + security_counter + CRC32). Q2 chỉ dùng Bank0.
*   [ ] **(Q2)** Kiểm tra Bộ đếm phiên bản đơn điệu (`security_counter` trong metadata so với `manifest.security_version`) để từ chối Firmware cũ. Persist counter khi boot slot mới OK.
*   [ ] **(Q2)** Bootloader boot-path tối thiểu: đọc metadata Bank0 → verify CRC32 → chọn active_slot → set `SCB->VTOR` → disable IRQ + SysTick → jump. (Full-image hash verify là Q3.)
*   [ ] **(Q3)** Quản lý Metadata nguyên tử bằng "Ping-Pong" (2 bank × 4 KB tại 0x0801_E000 và 0x0801_F000) với seq counter + CRC32 để chống mất điện. Q2 có thể tạm chấp nhận "không rút điện khi commit" trong kịch bản demo.
*   [ ] **(Q3)** Bootloader cold-boot verify: xác minh ASCON-Hash256 full-image (phủ toàn bộ plaintext slot sau decrypt và reassemble) + Ed25519 signature. Patch 1 byte → jump bị block, auto rollback slot trước.
*   [ ] **(Q3)** Bảo vệ phần cứng: RDP **Level 1** + WRP cho vùng Bootloader (0x0800_0000 – 0x0800_3FFF). ⚠ **Tránh RDP Level 2 ở Q2/Q3** — one-way, chỉ cân nhắc cho silicon thương mại cuối ở Q4.

**B. Thực thi Mật mã & Bắt tay (Cryptography Execution)**
*   [ ] **(Q2)** Parser manifest binary: đọc `ota_manifest_t` theo layout packed từ `common/manifest_def.h`, validate `magic == 0x4F54414D` + bounds-check mọi trường độ dài (`fw_size`, `total_chunks`, `chunk_size`) trước khi truy cập. **(Q4)** Thay bằng CBOR parser tối giản (subset RFC 8949) kèm fuzzer test ≥ 100 k input.
*   [ ] **(Q2)** Xác minh chữ ký Ed25519 của Manifest bằng Public Key của Root Authority hardcode trong ROM (qua uECC).
*   [ ] **(Q2)** Xác minh ASCON-Hash256 plaintext sau khi reassembly khớp `manifest.fw_hash[32]` trước khi commit.
*   [ ] **(Q2)** ECDHE X25519 qua uECC: sinh cặp khóa tạm thời, gửi pubkey qua `PKT_SESSION_KEY`, tính Shared Secret khi nhận pubkey Server.
*   [ ] **(Q2)** Dẫn xuất khóa phiên bằng **ASCON-XOF128** (reuse `permutations.c`): `K_sess = ASCON-XOF128(SS ‖ salt ‖ "OTA_Transport_v1")`. Bắt buộc domain separation context. KHÔNG dùng HKDF.
*   [ ] **(Q3)** Trích xuất Entropy phần cứng: nhiễu ADC thả nổi + Timer Jitter + RCT (Repetition Count Test) + APT (Adaptive Proportion Test) theo NIST SP 800-90B. Q2 có thể tạm dùng nonce đã nhận từ server (challenge-from-server mode) để demo.
*   [ ] **(Q3)** Derive DMK từ $K_{anchor}$ lưu cứng trong Bootloader; session key chain: `K_sess = ASCON-XOF128(DMK ‖ SS ‖ "Session_v1")` thay vì dùng SS trực tiếp.

**C. Vệ sinh Mật mã & Chống Tấn công Kênh bên (Secure Coding)**
*   [ ] **(Q2)** **Zeroization:** xóa sạch $K_{Session}$ và ECDHE private key ngay sau khi giải mã xong. Dùng hàm `secure_zeroize` với con trỏ `volatile` hoặc `__asm__ volatile("" ::: "memory")` barrier để lách Dead Store Elimination của GCC.
*   [ ] **(Q2)** **Constant-Time tag compare:** khi xác minh Tag của ASCON-128a, dùng phép tích lũy bitwise (`diff |= a[i] ^ b[i]`) thay `memcmp` để chống timing attack.
*   [ ] **(Q2)** **Fail-Secure:** phát hiện Tag sai trên 1 chunk / Ed25519 sai → gọi Erase Flash slot B lập tức + dừng session + clear metadata pending.
*   [ ] **(Q2)** Nạp lại IWDG chiến lược giữa các phép ASCON/Ed25519 dài (Ed25519 verify 500 ms–2 s có thể trigger WDT default 26 s nhưng vẫn nên refresh).
*   [ ] **(Q2)** Hủy khởi tạo (De-Init): `__disable_irq()`, stop SysTick + DMA + USART + I2C trước khi Bootloader jump sang Application. Clear SRAM nhạy cảm (stack region) nếu cần.

**D. Demo payload trên OLED (Q2 — minh chứng trực quan OTA)**
*   [ ] **(Q2)** SSD1306 driver (I2C1, PB6 = SCK, PB7 = SDA) trong `display_driver.c/h`. Framebuffer 1 KB + font 6×8.
*   [ ] **(Q2)** `display_screens.c/h`: 6 screen states khớp OTA state machine (IDLE/AUTH/DOWNLOAD/VERIFY/COMMIT/ERROR).
*   [ ] **(Q2)** Demo bitmap khác nhau giữa firmware v1 và v2 để khán giả thấy ngay OTA đã thay đổi app. Throttle refresh 5 Hz trong pha DOWNLOAD để không cạnh tranh I2C bus với UART.