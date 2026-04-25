# Pinout — ASCON-CRA-OTA

Tài liệu mô tả sơ đồ chân (pinout) và kết nối phần cứng giữa các thành phần trong hệ thống OTA:
**Server (PC) ↔ Gateway (ESP32-S3) ↔ Node (STM32F103 Blue Pill) ↔ OLED 0.96"**.

Phần cứng cố định (xem [hw_used.md](hw_used.md)):

- Gateway: ESP32-S3 N16R8 (16 MB Flash + 8 MB PSRAM, WiFi/BLE5)
- Node: STM32F103C8T6 (128 KB Flash, 20 KB SRAM, 72 MHz Cortex-M3)
- Display: OLED 0.96" SSD1306 I²C (driver SSD1306 hoặc SH1106)

---

## 1. Tổng quan kết nối

```
   Server (PC, Python)
   ┌──────────────────┐
   │  GUI + crypto    │
   │  manifest sign   │
   │  chunk encrypt   │
   └────────┬─────────┘
            │ WiFi / TCP
            ▼
   Gateway (ESP32-S3 N16R8)
   ┌──────────────────┐
   │  WiFi STA +      │
   │  UART bridge +   │
   │  firmware cache  │
   └────────┬─────────┘
            │ UART1 115200 8N1
            ▼
   Node (STM32F103C8T6 Blue Pill)        OLED 0.96"
   ┌──────────────────┐   I²C1 400 kHz   ┌─────────────┐
   │ OTA state mach.  │   PB6 = SCK      │  SSD1306    │
   │ + bootloader     │◄────────────────►│  128 × 64   │
   │ + flash driver   │   PB7 = SDA      │   mono      │
   └──────────────────┘                  └─────────────┘
```

- Gateway ↔ Node: UART bất đồng bộ, **115 200 baud, 8-N-1**, không flow control.
- Gateway ↔ Server: WiFi Station (TCP/HTTP cho Q2; MQTT + TLS Q4), cấu hình qua `CONFIG_WIFI_SSID`, `CONFIG_WIFI_PASSWORD`.
- Node ↔ OLED: I²C1 master @ 400 kHz, địa chỉ slave SSD1306 mặc định `0x3C`.

---

## 2. ESP32-S3 N16R8 Gateway (board `esp32-s3-devkitc-1`)

Cấu hình trong [main.c](../../2_gateway_esp32/main/main.c) và [uart_bridge.c](../../2_gateway_esp32/main/uart_bridge.c).

| Chức năng              | Peripheral       | GPIO         | Ghi chú                                                         |
| ---------------------- | ---------------- | ------------ | --------------------------------------------------------------- |
| UART bridge to Node TX | UART1 TX         | GPIO 17      | Nối tới PA10 (USART1 RX) của STM32                              |
| UART bridge to Node RX | UART1 RX         | GPIO 18      | Nối tới PA9 (USART1 TX) của STM32                               |
| GND                    | —                | GND          | Nối chung với GND của STM32                                     |
| 3V3 (tuỳ chọn)         | —                | 3V3          | Cấp nguồn cho Blue Pill khi không dùng USB                      |
| Console / Log          | USB-Serial-JTAG  | GPIO 19/20   | Cổng USB native trên DevKitC, 115 200 baud                      |
| WiFi                   | Internal         | —            | STA mode, WPA2-PSK (2.4 GHz, 802.11 b/g/n)                      |

> ⚠ Trên ESP32-S3 N16R8 (octal PSRAM), **GPIO 26–37** dành cho SPI Flash + Octal PSRAM nội bộ, **không được dùng**. GPIO 0/3 là strapping pin cho boot mode — tránh dùng cho UART. GPIO 17/18 đã chọn ngoài vùng cấm.

**Tham số UART1:**

- Baud rate: `115200`
- Data bits: `8`, Stop bits: `1`, Parity: `None`
- Flow control: `Disabled`
- RX buffer: `2048 byte` (xem `uart_driver_install`)

---

## 3. STM32F103C8T6 Node (Blue Pill, 128 KB Flash)

Cấu hình trong [system_init.c](../../3_node_stm32/application/src/system_init.c).

| Chức năng              | Peripheral  | Pin   | Ghi chú                                          |
| ---------------------- | ----------- | ----- | ------------------------------------------------ |
| UART to Gateway TX     | USART1 TX   | PA9   | Nối tới GPIO 18 (UART1 RX) của ESP32-S3          |
| UART to Gateway RX     | USART1 RX   | PA10  | Nối tới GPIO 17 (UART1 TX) của ESP32-S3          |
| OLED I²C SCK           | I²C1 SCL    | PB6   | Tới chân SCL của module SSD1306 (pull-up sẵn)    |
| OLED I²C SDA           | I²C1 SDA    | PB7   | Tới chân SDA của module SSD1306 (pull-up sẵn)    |
| LED heartbeat / debug  | GPIO Output | PC13  | Active-low trên Blue Pill                        |
| SWDIO                  | SWD         | PA13  | Nạp/debug qua ST-Link                            |
| SWCLK                  | SWD         | PA14  | Nạp/debug qua ST-Link                            |
| NRST                   | Reset       | NRST  | Nối tới RST của ST-Link (tuỳ chọn)               |
| HSE                    | Clock       | PD0/1 | Thạch anh 8 MHz, PLL ×9 → SYSCLK 72 MHz          |
| VBAT / 3V3             | Power       | 3V3   | 3.3 V logic                                      |
| GND                    | Power       | GND   | Nối chung với GND của ESP32-S3 và OLED           |

**Tham số USART1:**

- Baud rate: `115200`, 8-N-1, no flow control, oversampling 16, NVIC priority 5.

**Tham số I²C1 (cho OLED):**

- Standard mode 100 kHz (an toàn) hoặc Fast mode 400 kHz (refresh nhanh hơn cho progress bar).
- 7-bit addressing; SSD1306 mặc định `0x3C` (vài module 4-pin = `0x3D`).
- Master mode, không clock stretching.

**Clock tree:**

- HSE = 8 MHz → PLLMUL ×9 → SYSCLK = 72 MHz
- AHB = 72 MHz, APB1 = 36 MHz (I²C trên đây), APB2 = 72 MHz (USART1, GPIO)
- Flash latency: 2 wait states

---

## 4. OLED 0.96" SSD1306 I²C

| Pin module | Tên   | Nối tới STM32       | Ghi chú                                     |
| ---------- | ----- | ------------------- | ------------------------------------------- |
| 1          | GND   | GND                 | Đất chung                                   |
| 2          | VCC   | 3V3                 | 3.3 V (5 V cũng OK với module có LDO)        |
| 3          | SCL   | PB6 (I²C1 SCL)      | Pull-up 4.7 kΩ → 3V3 (thường tích hợp module) |
| 4          | SDA   | PB7 (I²C1 SDA)      | Pull-up 4.7 kΩ → 3V3 (thường tích hợp module) |

Driver: SSD1306 (mặc định) hoặc SH1106 (chỉ vài module). Phân giải 128 × 64, framebuffer 1 KB
mono. Refresh toàn màn ở 400 kHz mất ~25 ms — throttle 5 Hz trong pha DOWNLOAD để không
cạnh tranh CPU với UART bridge.

---

## 5. Sơ đồ đấu dây tổng thể

```
   ESP32-S3        STM32F103C8T6     OLED SSD1306
   ┌─────────┐    ┌──────────────┐    ┌──────────┐
   │GPIO17 TX│───►│PA10 USART1 RX│    │          │
   │GPIO18 RX│◄───│PA9  USART1 TX│    │          │
   │GND      │────│GND           │────│GND       │
   │3V3 (opt)│───►│3V3           │───►│VCC (3V3) │
   │         │    │PB6 I²C1 SCL  │───►│SCL       │
   │         │    │PB7 I²C1 SDA  │◄──►│SDA       │
   └─────────┘    └──────────────┘    └──────────┘
```

> ⚠ Nối chung GND giữa cả 3 thiết bị trước khi cấp nguồn. Không nối chéo TX↔TX hay
> SDA↔SCL. ESP32-S3, STM32 và SSD1306 đều logic 3.3 V — không cần level shifter.

---

## 6. Bộ nhớ Flash Node (memory map tóm tắt)

Layout đầy đủ xem [3_node_stm32/docs/flash_map.md](../../3_node_stm32/docs/flash_map.md)
và [system_overview.md §3.3](system_overview.md). Tóm tắt cho STM32F103C8T6 128 KB:

| Vùng                  | Địa chỉ bắt đầu | Kích thước | Ghi chú                                      |
| --------------------- | --------------- | ---------- | -------------------------------------------- |
| Bootloader            | `0x0800_0000`   | 16 KB      | Verify manifest + chọn slot + VTOR jump      |
| Application Slot A    | `0x0800_4000`   | 52 KB      | Firmware đang chạy                           |
| Application Slot B    | `0x0801_1000`   | 52 KB      | OTA staging (ghi chunk giải mã vào đây)      |
| Boot metadata Bank0   | `0x0801_E000`   | 4 KB       | `boot_metadata_t` (Q2 dùng bank này)         |
| Boot metadata Bank1   | `0x0801_F000`   | 4 KB       | Ping-pong (Q3)                               |

> Page size flash STM32F103 medium-density = 1 KB, khớp với `chunk_size` 1024 B trong
> `ota_manifest_t`.

---

## 7. Công cụ nạp & debug

| Thành phần | Giao tiếp nạp                  | Công cụ                          |
| ---------- | ------------------------------ | -------------------------------- |
| ESP32-S3   | USB native (USB-Serial-JTAG)   | `pio run -t upload`, `esptool.py`|
| STM32 Node | SWD (PA13/PA14)                | ST-Link V2 + `stlink` / OpenOCD  |
| Monitor    | USB-Serial cả hai              | `pio device monitor -b 115200`   |

---

## 8. Ghi chú triển khai

- Khi đổi chân UART của ESP32-S3, cập nhật `UART_NODE_TX_PIN` và `UART_NODE_RX_PIN` trong [main.c](../../2_gateway_esp32/main/main.c) **và** đối chiếu với GPIO matrix S3 (tránh vùng dành cho octal PSRAM 33–37 và SPI flash 27–32).
- Khi đổi USART hoặc chân I²C của STM32, cập nhật `MX_USART1_UART_Init()`, `MX_I2C1_Init()` trong [system_init.c](../../3_node_stm32/application/src/system_init.c) và remap GPIO tương ứng.
- Module SSD1306 thường có sẵn pull-up 4.7 kΩ trên SDA/SCL. Nếu module không có, **phải gắn ngoài** (4.7–10 kΩ → 3V3) để I²C1 hoạt động.
- Nếu chạy hai thiết bị ở hai nguồn cấp khác nhau, bắt buộc nối GND chung để tránh trôi mức logic gây lỗi UART/I²C.
