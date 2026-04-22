Dưới góc độ kiến trúc hệ thống E2E (End-to-End) và an toàn thông tin, hệ thống OTA của bạn được phân tách thành 3 miền rõ rệt: **Server (Root Authority)**, **ESP32-S3 (Edge Gateway)**, và **STM32F103 (End Node)**. Mỗi thiết bị đảm nhận một vai trò cụ thể trong mô hình đe dọa (Threat Model) và ngân sách tài nguyên.

Dưới đây là bộ checklist kỹ thuật và bảo mật chuyên sâu, được thiết kế riêng cho từng thực thể trong hệ thống ASCON-CRA:

> **Phase tags:** `(Q2)` = MVP demo-able end-to-end; `(Q3)` = Hardening (RDP/WRP, CBOR canonical, DMK, constant-time audit); `(Q4)` = Field trial multi-node + production server. Không đánh tag = nền tảng, bắt buộc từ Q2.

### 1. Checklist cho Server (Root Authority - Máy chủ Cấp phát)
Máy chủ là nơi tin cậy tuyệt đối, chịu trách nhiệm sinh khóa, đóng gói và ký số.

**A. Đóng gói & Mã hóa Firmware (Packaging & Encryption)**
*   [ ] Sinh ngẫu nhiên Khóa nội dung tĩnh ($K_{FW}$) 16 bytes và $Nonce_{Base}$ 16 bytes cho mỗi bản build firmware.
*   [ ] Phân mảnh (Chunking) firmware thành các khối 1024 bytes (khớp với kích thước Page của Flash STM32).
*   [ ] Mã hóa từng khối bằng ASCON-128a. Đảm bảo vệ sinh Nonce bằng công thức: $Nonce_i = Nonce_{Base} \oplus i$.
*   [ ] Đính kèm Associated Data (AD) vào ASCON-128a chứa "Model" và "Version" để chống tấn công Rollback ngay từ lớp mật mã.

**B. Quản lý Manifest & Chữ ký số**
*   [ ] Tạo Manifest chứa: Version, Kích thước Firmware, ASCON-Hash256 của toàn bộ Ciphertext, $Nonce_{Base}$, và Salt cho KDF.
*   [ ] **(Q2)** Chuẩn hóa Manifest về định dạng nhị phân cố định (`ota_manifest_t` trong `common/manifest_def.h`, little-endian, packed) để đảm bảo tính tất định trước khi ký. **(Q3)** Chuyển sang Canonical CBOR (RFC 8949 §4.2.1 Core Deterministic Encoding); bump `MANIFEST_VERSION` và cập nhật đồng bộ cả 3 thành phần (server builder + node parser + gateway relay).
*   [ ] Dùng khóa riêng Ed25519 để ký lên toàn bộ chuỗi byte của Manifest (trừ trường chứa chữ ký).

**C. Handshake & Bảo mật Chuyển tiếp (Forward Secrecy)**
*   [ ] Sinh cặp khóa tạm thời (ephemeral keys) X25519 ($sk_{srv}, pk_{srv}$) cho mỗi phiên cập nhật của thiết bị.
*   [ ] Tính toán Shared Secret (SS) và dẫn xuất Khóa phiên ($K_{Session}$) thông qua hàm ASCON-XOF.
*   [ ] "Gói" (Key Wrap) khóa $K_{FW}$ bằng $K_{Session}$ sử dụng ASCON-128a.
*   [ ] Ký số lên Payload Handshake ($pk_{srv} || Wrapped\_K$) để thiết bị STM32 chống lại tấn công MITM từ chính ESP32 Gateway.
*   [ ] **(Q3)** Triển khai Hierarchical Key Management: server lưu $K_{anchor}$ 32 B riêng cho từng node (not shared). Derive Device Master Key per-device: $DMK = ASCON\text{-}XOF(K_{anchor} \| device\_id \| \text{"DMK\_v1"})$. Mất 1 anchor không ảnh hưởng các node còn lại trong fleet.

---

### 2. Checklist cho ESP32-S3 (Edge Gateway - Cổng Biên)
ESP32-S3 hoạt động như một Proxy và Cache. Nó sở hữu tài nguyên lớn (Wi-Fi, 16MB Flash, 8MB PSRAM) nhưng **không được tin cậy** để giữ các khóa bí mật của STM32.

**A. Giao tiếp Mạng & Bộ nhớ đệm (Networking & Caching)**
*   [ ] **(Q2)** Thiết lập kết nối HTTP trong LAN tới Server Python (SSID WiFi hardcode chấp nhận được cho demo) để pull manifest + ciphertext chunks. **(Q4)** Chuyển sang MQTT broker (Mosquitto) hoặc HTTPS + token auth + certificate pinning cho fleet deployment thực.
*   [ ] Phân bổ vùng nhớ PSRAM hoặc phân vùng SPI Flash (Sử dụng hệ thống tệp FATFS/SPIFFS hoặc Raw Partition) để lưu trữ đệm (Cache) toàn bộ cục Ciphertext và Manifest.
*   [ ] Tính toán checksum (MD5/CRC32) độc lập của file tải về để đảm bảo tính toàn vẹn cơ bản ở tầng mạng trước khi đẩy xuống STM32.

**B. Xử lý Giao thức Proxy (Bridge Logic)**
*   [ ] Hoạt động như một "Transparent Proxy" trong pha Bắt tay ECDHE. Chuyển tiếp nguyên vẹn `ClientHello` từ STM32 lên Server và `ServerHello` từ Server xuống STM32. Tuyệt đối không can thiệp vào tham số mật mã.
*   [ ] Triển khai máy trạng thái (FSM) quản lý giao tiếp UART/SPI với STM32.
*   [ ] Thiết lập luồng truyền Chunk (Streaming): Chờ tín hiệu `ACK` từ STM32 sau khi ghi Flash thành công thì mới truyền Chunk tiếp theo. Xử lý timeout và retry.

---

### 3. Checklist cho STM32F103 (End Node - Nút Đích)
Đây là môi trường khắc nghiệt nhất. Yêu cầu tối ưu ROM/RAM cực hạn và phòng thủ vật lý.

**A. Cấu trúc Flash & Bootloader (Resilience)**
*   [ ] Cấu hình Flash Map (STM32F103CBT6 — 128 KB): 16KB Bootloader, 52KB Slot A, 52KB Slot B, 8KB Metadata (2× 4KB ping-pong bank). Page size 1 KB khớp với chunk size 1024 B.
*   [ ] **(Q3)** Kích hoạt bảo vệ phần cứng: RDP **Level 1** + WRP cho vùng Bootloader (0x0800_0000 – 0x0800_3FFF). ⚠ **Tránh RDP Level 2 ở Q2/Q3** — không thể tắt sau khi set (one-way), chỉ cân nhắc cho silicon thương mại cuối ở Q4 sau khi toolchain đã hoàn toàn ổn định.
*   [ ] Quản lý Metadata nguyên tử bằng cơ chế "Bộ đệm Ping-Pong" (2 bank × 4 KB tại 0x0801_E000 và 0x0801_F000) với seq counter + CRC32 trên mỗi record để đảm bảo không hỏng thiết bị khi mất điện đột ngột.
*   [ ] Kiểm tra Bộ đếm phiên bản đơn điệu (`security_version` trong metadata, khớp `manifest.security_version`) để từ chối Firmware cũ (Anti-rollback).
*   [ ] **(Q2)** Bootloader boot-path: đọc cả 2 bank metadata → chọn record có `seq_counter` lớn nhất và CRC hợp lệ → verify `ASCON-Hash256(slot)` khớp `slot_hash` trong metadata → set `SCB->VTOR` trỏ tới slot active → jump. Fallback slot cũ nếu hash mismatch.
*   [ ] **(Q3)** Bootloader cold-boot verify: xác minh chữ ký Ed25519 full-image (phủ toàn bộ plaintext slot sau khi giải mã và reassembled), không chỉ manifest. Patch 1 byte trong slot → jump bị block, auto rollback về slot trước.

**B. Thực thi Mật mã & Bắt tay (Cryptography Execution)**
*   [ ] **(Q2)** Parser manifest binary: đọc `ota_manifest_t` theo layout packed từ `common/manifest_def.h`, validate `magic == 0x4F54414D` + bounds-check mọi trường độ dài (`fw_size`, `total_chunks`) trước khi truy cập. **(Q3)** Thay bằng CBOR parser tối giản (subset RFC 8949) kèm fuzzer test ≥ 100 k input chống Buffer Overflow.
*   [ ] Xác minh chữ ký Ed25519 của Manifest bằng Public Key của Root Authority được hardcode trong ROM.
*   [ ] Trích xuất Entropy phần cứng: Sinh số ngẫu nhiên từ nhiễu ADC thả nổi và Timer Jitter. Áp dụng RCT (Repetition Count Test) và APT (Adaptive Proportion Test).
*   [ ] Thực thi ECDHE X25519: Sinh cặp khóa tạm thời, gửi cho ESP32. Tính toán Shared Secret khi nhận phản hồi từ Server.
*   [ ] Dẫn xuất khóa phiên $K_{Session}$ bằng hàm ASCON-XOF, đảm bảo có sử dụng biến ngữ cảnh `Info` (Domain Separation): `K_sess = ASCON-XOF(ECDHE_shared ‖ salt ‖ "OTA_Transport_v1")`.
*   [ ] **(Q3)** Derive DMK từ $K_{anchor}$ lưu cứng trong Bootloader (application truy cập qua syscall protected); session key chain: `K_sess = ASCON-XOF(DMK ‖ ECDHE_shared ‖ "Session_v1")` thay vì dùng ECDHE_shared trực tiếp.

**C. Vệ sinh Mật mã & Chống Tấn công Kênh bên (Secure Coding)**
*   [ ] **Zeroization:** Xóa sạch $K_{Session}$, $K_{FW}$, và private key $sk_{dev}$ ngay khi giải mã xong. Bắt buộc dùng hàm `secure_zeroize` với con trỏ `volatile` hoặc rào cản bộ nhớ (memory barrier) để lách tính năng loại bỏ mã chết (Dead Store Elimination) của trình biên dịch.
*   [ ] **Constant-Time:** Khi xác minh Thẻ Tag của ASCON-128a, sử dụng phép toán bitwise logic (Tích lũy XOR/OR) thay vì dùng `memcmp` thoát sớm (early-exit) để chống tấn công rò rỉ thời gian (Timing Attack).
*   [ ] **Fail-Secure:** Ngay khi phát hiện Tag ASCON sai lệch trên một khối 1KB, hoặc sai chữ ký, phải gọi hàm Erase Flash (Security Wipe) lập tức trên Slot B và dừng cập nhật.
*   [ ] Nạp lại Watchdog Timer (IWDG) chiến lược bên trong vòng lặp giải mã ASCON để tránh hệ thống tự Reset do hiểu nhầm bị treo.
*   [ ] Hủy khởi tạo (De-Init): Tắt ngắt toàn cục (`__disable_irq()`), dừng SysTick và các ngoại vi trước khi Bootloader Jump sang Firmware ứng dụng.