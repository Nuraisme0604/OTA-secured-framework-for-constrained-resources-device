> **Lưu ý đọc:** tài liệu này mô tả *ý tưởng mục tiêu*. Thực trạng triển khai phân theo phase Q2/Q3/Q4 — xem [§Phase triển khai](#phase-triển-khai) ở cuối. Q2 là MVP bắt buộc demo end-to-end; Q3 là hardening; Q4 là production.

Ý tưởng cốt lõi của nghiên cứu là thiết kế và hiện thực hóa một kiến trúc cập nhật phần mềm qua mạng (OTA) mang tên **ASCON-CRA**, nhằm giải quyết "bài toán nan giải" giữa ba yếu tố: khả năng mở rộng quy mô, hiệu suất trên phần cứng hạn chế và khả năng bảo trì an ninh dài hạn cho hệ sinh thái IoT. Giải pháp này được thiết kế chuyên biệt cho các vi điều khiển Lớp 0/1 (như STM32F103CBT6 với 128KB Flash và 20KB SRAM) vốn không đủ tài nguyên để chạy các giao thức nặng nề như TLS truyền thống, đồng thời vá lỗ hổng thiếu hụt tính năng Bảo mật chuyển tiếp (PFS) trong các chuẩn OTA hiện tại như IETF SUIT.

Kiến trúc ASCON-CRA được xây dựng dựa trên sự giao thoa của ba trụ cột công nghệ mật mã:

**1. Mật mã hạng nhẹ ASCON (Lightweight Cryptography)**
Hệ thống sử dụng bộ tiêu chuẩn ASCON (NIST SP 800-232) để thay thế hoàn toàn AES-GCM trong việc bảo vệ dữ liệu. Dựa trên cấu trúc bọt biển (Sponge) với trạng thái nội bộ 320-bit, ASCON-128a cung cấp Mã hóa Xác thực với Dữ liệu Liên kết (AEAD). ASCON cực kỳ tối ưu cho vi điều khiển kiến trúc 32-bit như ARM Cortex-M3 vì nó chỉ sử dụng các phép toán bitwise (XOR, AND, ROT), giúp đạt thông lượng cao mà không cần bộ tăng tốc mật mã phần cứng, đồng thời thu nhỏ tối đa footprint ROM/RAM. Trong giao thức, ASCON-128a mã hóa các khối (chunk) firmware 1KB, đảm bảo tính bí mật và dùng thẻ Tag 128-bit để xác minh tính toàn vẹn trên từng khối trước khi ghi vào Flash.

**2. Bảo mật chuyển tiếp hoàn hảo (Perfect Forward Secrecy - PFS)**
Để ngăn chặn kịch bản thảm họa "Thu thập bây giờ, giải mã sau" (Harvest Now, Decrypt Later), giao thức từ chối việc sử dụng khóa tĩnh dài hạn để mã hóa dữ liệu. Thay vào đó, nó ứng dụng cơ chế Trao đổi khóa Diffie-Hellman trên Đường cong Elliptic tạm thời (ECDHE) thông qua Curve25519 (X25519). Ở mỗi phiên OTA, thiết bị và máy chủ sinh ra một cặp khóa tạm thời mới để thiết lập bí mật chung. Khóa giải mã thực sự ($K_{FW}$) được máy chủ bọc (wrap) bằng khóa phiên ($K_{sess}$) sinh ra từ ECDHE. Ngay sau khi firmware được giải mã, mọi tài sản mật mã tạm thời đều bị xóa sạch (zeroized). Nếu kẻ tấn công có trích xuất được khóa vật lý của thiết bị trong tương lai, chúng cũng không thể giải mã các bản firmware trong quá khứ do các khóa tạo nên phiên làm việc đã bị hủy vĩnh viễn.

**3. Quản lý Khóa Phân cấp (Hierarchical Key Management - HKM)**
Vì vi điều khiển không có đủ không gian lưu trữ an toàn cho hàng loạt khóa, hệ thống nhắm tới mô hình HKM dựa trên "Trích xuất và Mở rộng" (Extract-then-Expand). **Q3 mục tiêu**: thiết bị chỉ lưu duy nhất một Khóa neo (Trust Anchor / $K_{anchor}$) 256-bit cấp phép tại nhà máy; từ đó dẫn xuất Device Master Key (DMK) per-device và Session Key ($K_{sess}$) qua **ASCON-XOF128** (KDF) với salt + chuỗi ngữ cảnh ("OTA_Transport_v1") để phân tách miền (Domain Separation). **Q2 hiện trạng**: dùng cấu hình *phẳng* — chỉ X25519 ECDHE + ASCON-XOF128 trực tiếp ra $K_{sess}$, chưa có $K_{anchor}$/DMK. Code Python hiện wire HKDF cần migrate qua `pyascon.ascon_xof128`. Việc giữ ASCON-XOF (không lùi về HKDF) là điều kiện để duy trì luận điểm "primitive unification" — toàn bộ pipeline chỉ cần ASCON permutation.

**Kiến trúc Hệ thống và Quy trình Vận hành Thực tiễn**

Ý tưởng triển khai hệ thống xoay quanh mô hình ba tác nhân E2E (End-to-End):
*   **Root Authority (Máy chủ):** Tạo tệp kê khai Manifest chứa siêu dữ liệu (version, kích thước, ASCON-Hash256, Nonce, Salt) và ký số bằng Ed25519. Định dạng manifest: **Q2 dùng binary packed `ota_manifest_t` 212 B** (`common/manifest_def.h`), **Q4 chuyển sang CBOR deterministic (RFC 8949 §4.2.1)**. Máy chủ mã hóa tĩnh firmware bằng $K_{FW}$ (Q3 — hiện Q2 server truyền key phiên trực tiếp), sau đó bọc (wrap) $K_{FW}$ bằng khóa phiên ECDHE khi kết nối với thiết bị (Q3).
*   **Edge Gateway (ESP32-S3 N16R8 — chốt phần cứng):** WiFi 2.4 GHz + BLE5, 16 MB Flash, 8 MB PSRAM, 240 MHz dual-core. Vai trò: proxy + cache firmware đã mã hóa tĩnh + manifest, transparent cho handshake ECDHE giữa Server ↔ Node. UART bridge sang STM32 trên GPIO 17/18 (xem [pinout.md](pinout.md)). Q2 dùng DRAM nội cho cache 52 KB; Q3 mở rộng dùng PSRAM khi fleet hoặc firmware lớn hơn. **Code Q2 phải đổi `2_gateway_esp32/platformio.ini` từ `esp32dev` sang `esp32-s3-devkitc-1`.**
*   **End Node (STM32F103C8T6 — chốt phần cứng):** Blue Pill 72 MHz Cortex-M3, 128 KB Flash, 20 KB SRAM. Thực thi Secure Bootloader, xác minh chữ ký Ed25519 của Manifest bằng public key của Root Authority hardcode trong ROM, thiết lập khóa qua ECDHE X25519, dẫn xuất $K_{Session}$ qua ASCON-XOF128, nhận firmware theo từng đoạn 1 KB và giải mã bằng ASCON-128a AEAD. Hiển thị trạng thái + demo payload trên **OLED 0.96" SSD1306** qua I²C1 (PB6 = SCK, PB7 = SDA) — chứng minh OTA thay đổi nội dung app trực quan.

**Bảo vệ Vi kiến trúc và Khả năng Phục hồi (Resilience)**

Để biến giao thức mật mã thành một giải pháp nhúng an toàn trong thực tế, ý tưởng tích hợp các cơ chế phòng thủ cấp thấp:
*   **Flash Map và A/B Partitioning (Q2):** Bộ nhớ Flash 128 KB quy hoạch thành Bootloader (16 KB) + Slot A (52 KB) + Slot B (52 KB) + Metadata region (8 KB, dành chỗ sẵn cho 2 bank ping-pong Q3, Q2 chỉ dùng Bank0). Firmware mới ghi vào Slot B; nếu Tag ASCON sai → Fail-Secure (erase Slot B + dừng). Bootloader hoán đổi logic bằng `SCB->VTOR` thay vì copy vật lý — chống bricking.
*   **Bộ đệm Ping-Pong cho Metadata (Q3):** Trạng thái OTA ghi vào 2 Bank Metadata × 4 KB luân phiên (seq counter + CRC32) để đạt tính nguyên tử và power-fail recovery. **Q2** tạm chấp nhận single-bank với CRC32 + giả định không rút điện trong pha COMMIT cho kịch bản demo.
*   **Chống tấn công hạ cấp (Anti-rollback, Q2):** Bootloader kiểm tra `security_counter` trong metadata so với `manifest.security_version`; mọi cố gắng cài manifest có version ≤ counter hiện tại đều bị từ chối với `OTA_ERR_VERSION_ROLLBACK (0x80)`.
*   **Vệ sinh Mật mã (Secure Zeroization, Q2 — audit Q3):** Hàm `secure_zeroize` dùng con trỏ `volatile` hoặc `__asm__ volatile("" ::: "memory")` barrier để ép GCC không tối ưu hóa bỏ (Dead Store Elimination). Wipe $K_{sess}$ + ECDHE private key ngay sau decrypt + commit. $K_{FW}$/wrap key chỉ tồn tại sau khi triển khai key wrap (Q3).
*   **Chống tấn công kênh bên (Constant-Time, Q2 baseline + Q3 audit):** Tag verify dùng phép tích lũy bitwise (`diff |= a[i] ^ b[i]`) thay `memcmp` early-exit. **Entropy bù TRNG (Q3)**: nhiễu ADC thả nổi + Timer jitter, đi kèm RCT (Repetition Count Test) + APT (Adaptive Proportion Test) theo NIST SP 800-90B. **Q2 demo** có thể tạm dùng nonce do server cấp (challenge-from-server) trong khi entropy hardware đang phát triển.

---

## Phase triển khai

| Trụ cột | Q2 (MVP demo) | Q3 (hardening) | Q4 (production) |
|---|---|---|---|
| ASCON-128a AEAD chunk | ✅ Server done; node tích hợp | Constant-time + zeroize audit | — |
| ASCON-XOF128 KDF | ⚠ Migrate Python (đang HKDF) + viết C cho STM32 | DMK chain | — |
| ASCON-Hash256 | ⚠ Migrate Python (đang SHA-256) + viết C cho STM32 | Full-image verify trong bootloader | — |
| Ed25519 sign + verify | ✅ Server; STM32 qua uECC | — | — |
| X25519 ECDHE ephemeral | ✅ Server; STM32 qua uECC | — | — |
| Manifest format | binary `ota_manifest_t` 212 B | — | CBOR deterministic RFC 8949 |
| HKM K_anchor → DMK → K_sess | flat (X25519+XOF) | full tree per-device | — |
| K_FW static + wrap | — | ✓ | — |
| Anti-rollback `security_counter` | persist single bank | ping-pong 2×4 KB + power-fail | — |
| Bootloader VTOR swap + jump | ✓ minimal (verify manifest) | full-image hash + sig verify | — |
| RDP / WRP | — | RDP1 + WRP boot region | RDP2 (cân nhắc) |
| Entropy hardware | nonce-from-server fallback | ADC + jitter + RCT/APT | — |
| Gateway hardware | ESP32-S3 N16R8 (chốt) | — | — |
| Gateway transport | HTTP/TCP LAN, hardcode WiFi | — | MQTT + TLS + cert pinning |
| Gateway cache | DRAM 52 KB | PSRAM 8 MB cho firmware lớn | — |
| Node hardware | STM32F103C8T6 128 KB / 20 KB (chốt) | — | — |
| OLED demo (SSD1306 PB6/PB7) | ✓ — minh chứng OTA trực quan | — | — |
| Multi-node fleet | single node demo | — | server-side fleet mgmt |