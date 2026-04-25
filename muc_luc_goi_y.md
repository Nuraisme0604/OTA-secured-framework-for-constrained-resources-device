Giải pháp cập nhật OTA bảo mật cho thiết bị IoT tài nguyên thấp
sử dụng mật mã Ascon và quản lý khóa phân cấp

MỤC LỤC

Lời cảm ơn
Tóm tắt nội dung Đồ án
Bảng ký hiệu và chữ viết tắt
Danh sách bảng
Danh sách hình vẽ

Mở đầu
    Lý do chọn đề tài
    Mục tiêu nghiên cứu
    Phương pháp nghiên cứu
    Đóng góp của đề tài
    Bố cục Đồ án

Chương 1: Cơ sở lý thuyết
1.1. Bảo mật trên thiết bị IoT tài nguyên hạn chế
    1.1.1. Thuộc tính bảo mật nền tảng và khung phân tích STRIDE
    1.1.2. Phân loại IETF RFC 7228 và đặc thù Class-1 (case study STM32F103)
    1.1.3. Mô hình đe dọa đặc thù: rollback, replay, HNDL, side-channel
1.2. Cập nhật OTA trong hệ sinh thái IoT
    1.2.1. Khái niệm, quy trình và nghịch lý bảo mật của OTA
    1.2.2. Các chuẩn hiện hành (SUIT, TUF/Uptane) và giới hạn trên Class-1
1.3. Nguyên thủy mật mã sử dụng
    1.3.1. Mã hóa xác thực hạng nhẹ ASCON-128a
    1.3.2. Thỏa thuận khóa X25519 (ECDHE)
    1.3.3. Chữ ký số Ed25519 xác thực nguồn gốc firmware
    1.3.4. Dẫn xuất khóa ASCON-XOF128 và nguyên lý phân tách miền (primitive unification)
1.4. Công trình liên quan và khoảng trống nghiên cứu

Chương 2: Mô hình và giao thức ASCON-CRA
2.1. Phân tích yêu cầu và mối đe dọa
    2.1.1. Kịch bản triển khai và phạm vi bài toán
    2.1.2. Phân tích STRIDE trên quy trình OTA
    2.1.3. Giả thuyết nghiên cứu (PFS, kháng lạm dụng nonce, tối ưu tài nguyên)
2.2. Kiến trúc tổng thể
    2.2.1. Sơ đồ khối Server – Edge Gateway – End Device
    2.2.2. Mô hình mã hóa lai phân tách (Decoupled Hybrid Encryption)
    2.2.3. Phân định trách nhiệm end-to-end và vai trò Gateway
2.3. Quản lý khóa phân cấp (HKM)
    2.3.1. Cây khóa: Root Key → Device Master Key → Session Key
    2.3.2. Dẫn xuất khóa bằng ASCON-XOF128 và phân tách miền
    2.3.3. Key Evolution đảm bảo Forward Secrecy
    2.3.4. Sinh entropy trên MCU không có TRNG (ADC nhiễu + Timer jitter)
2.4. Giao thức ASCON-CRA
    2.4.1. Đóng gói và phân đoạn firmware độc lập (Independent Chunking)
    2.4.2. Bắt tay xác thực CRA và thiết lập khóa phiên qua Edge Gateway
    2.4.3. Truyền tải luồng và xác thực AEAD từng phân đoạn
    2.4.4. Commit, reboot và zeroization khóa phiên
2.5. Bộ nhớ và bootloader
    2.5.1. Flash map A/B Slot và metadata bootloader
    2.5.2. Logical swap qua thanh ghi VTOR
    2.5.3. Monotonic counter chống rollback
    2.5.4. Power-fail recovery
2.6. Triển khai hệ thống
    2.6.1. Server (Python): sinh khóa, ký manifest, đóng gói firmware
    2.6.2. Edge Gateway (ESP32-S3 N16R8): cầu WiFi–UART và relay OTA
    2.6.3. End Device (STM32F103C8T6): OTA state machine, crypto port, OLED demo payload
2.7. Kết quả thiết kế và đánh giá an ninh định tính
    2.7.1. Mức độ đáp ứng các giả thuyết (PFS, anti-rollback, anti-tamper)
    2.7.2. Phân tích dưới mô hình Dolev–Yao
    2.7.3. Bề mặt tấn công còn lại và giới hạn

Chương 3: Phương pháp thực nghiệm
3.1. Cấu hình thực nghiệm
    3.1.1. Phần cứng: STM32F103C8T6 @72 MHz (128 KB Flash, 20 KB RAM), ESP32-S3 N16R8, OLED 0.96" SSD1306, Logic Analyzer 8 ch, ST-Link V2
    3.1.2. Phần mềm, thư viện và toolchain (PlatformIO + STM32Cube HAL + ESP-IDF + uECC + pyascon)
    3.1.3. Công cụ đo (GPIO toggle + Logic Analyzer 24 MHz, map file của linker)
3.2. Phương pháp luận đo lường
    3.2.1. Chuẩn FELICS cho mã hóa hạng nhẹ
    3.2.2. Đo timing bằng GPIO instrumentation
    3.2.3. Đo ROM/RAM footprint từ map file và linker script
3.3. Kịch bản kiểm thử
    3.3.1. Cập nhật bình thường end-to-end (happy path)
    3.3.2. Chèn/sửa chunk — kiểm tra MAC failure
    3.3.3. Replay / man-in-the-middle trên kênh UART
    3.3.4. Downgrade firmware cũ — kiểm tra anti-rollback
    3.3.5. Mất điện trong khi ghi flash — power-fail recovery
3.4. Tiêu chí đánh giá
    3.4.1. Latency: handshake, chunk, end-to-end
    3.4.2. Footprint: ROM bootloader + application, RAM đỉnh
    3.4.3. Tiêu chí an ninh: PFS, anti-rollback, anti-tamper, anti-replay

Kết luận
    Khẳng định kết quả đạt được
    Đề xuất ứng dụng (Smart Hotel, hạ tầng IoT công nghiệp)
    Hạn chế và hướng nghiên cứu tiếp theo

Tài liệu tham khảo
