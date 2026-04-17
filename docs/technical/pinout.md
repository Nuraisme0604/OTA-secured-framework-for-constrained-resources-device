# Pinout — ASCON-CRA-OTA

Tài liệu mô tả sơ đồ chân (pinout) và kết nối phần cứng giữa các thành phần trong hệ thống OTA:
**Server (PC) ↔ Gateway (ESP32) ↔ Node (STM32F103 Blue Pill)**.

---

## 1. Tổng quan kết nối

```
 ┌─────────────┐        WiFi/MQTT        ┌─────────────┐        UART         ┌──────────────┐
 │   Server    │ ◄─────────────────────► │  ESP32 GW   │ ◄─────────────────► │  STM32 Node  │
 │  (Python)   │                         │  (esp32dev) │    115200 8N1       │ (BluePill)   │
 └─────────────┘                         └─────────────┘                     └──────────────┘
```

- Gateway ↔ Node: UART bất đồng bộ, **115200 baud, 8-N-1**, không flow control.
- Gateway ↔ Server: WiFi Station (TCP/MQTT), cấu hình qua `CONFIG_WIFI_SSID`, `CONFIG_WIFI_PASSWORD`.

---

## 2. ESP32 Gateway (board `esp32dev`)

Cấu hình trong [main.c](../../2_gateway_esp32/main/main.c) và [uart_bridge.c](../../2_gateway_esp32/main/uart_bridge.c).

| Chức năng        | Peripheral | GPIO    | Ghi chú                                 |
| ---------------- | ---------- | ------- | --------------------------------------- |
| UART to Node TX  | UART1 TX   | GPIO 17 | Nối tới PA10 (RX) của STM32             |
| UART to Node RX  | UART1 RX   | GPIO 16 | Nối tới PA9 (TX) của STM32              |
| GND              | —          | GND     | Nối chung với GND của STM32             |
| 3V3 (tuỳ chọn)   | —          | 3V3     | Có thể cấp nguồn cho Blue Pill nếu cần  |
| WiFi             | Internal   | —       | STA mode, WPA2-PSK                      |
| Console / Log    | UART0      | GPIO 1/3| USB-Serial debug, 115200 baud           |

**Tham số UART1:**

- Baud rate: `115200`
- Data bits: `8`, Stop bits: `1`, Parity: `None`
- Flow control: `Disabled`
- RX buffer: `2048 byte` (xem `uart_driver_install`)

---

## 3. STM32F103C8 Node (Blue Pill)

Cấu hình trong [system_init.c](../../3_node_stm32/application/src/system_init.c).

| Chức năng            | Peripheral  | Pin   | Ghi chú                                  |
| -------------------- | ----------- | ----- | ---------------------------------------- |
| UART to Gateway TX   | USART1 TX   | PA9   | Nối tới GPIO16 (RX) của ESP32            |
| UART to Gateway RX   | USART1 RX   | PA10  | Nối tới GPIO17 (TX) của ESP32            |
| LED debug            | GPIO Output | PC13  | Active-low trên Blue Pill                |
| SWDIO                | SWD         | PA13  | Nạp/debug qua ST-Link                    |
| SWCLK                | SWD         | PA14  | Nạp/debug qua ST-Link                    |
| NRST                 | Reset       | NRST  | Nối tới RST của ST-Link (tuỳ chọn)       |
| HSE                  | Clock       | PD0/1 | Thạch anh 8 MHz, PLL ×9 → SYSCLK 72 MHz  |
| VBAT / 3V3           | Power       | 3V3   | 3.3 V logic                              |
| GND                  | Power       | GND   | Nối chung với GND của ESP32              |

**Tham số USART1:**

- Baud rate: `115200`
- Word length: `8 bit`, Stop bits: `1`, Parity: `None`
- Mode: `TX + RX`
- Flow control: `None`
- Oversampling: `16`
- NVIC priority: `5`

**Clock tree:**

- HSE = 8 MHz → PLLMUL ×9 → SYSCLK = 72 MHz
- AHB = 72 MHz, APB1 = 36 MHz, APB2 = 72 MHz
- Flash latency: 2 wait states

---

## 4. Sơ đồ đấu dây ESP32 ↔ STM32

```
   ESP32 (esp32dev)                    STM32F103 (Blue Pill)
  ┌──────────────────┐                ┌──────────────────────┐
  │  GPIO17 (U1 TX)  │ ─────────────► │ PA10 (USART1 RX)     │
  │  GPIO16 (U1 RX)  │ ◄───────────── │ PA9  (USART1 TX)     │
  │  GND             │ ─────────────  │ GND                  │
  │  3V3 (optional)  │ ─────────────► │ 3V3 (nếu cấp nguồn)  │
  └──────────────────┘                └──────────────────────┘
```

> ⚠️ Luôn **nối chung GND** trước khi cấp nguồn. Không nối chéo TX↔TX / RX↔RX.
> ⚠️ STM32 Blue Pill dùng **logic 3.3 V** — tương thích trực tiếp với ESP32, không cần level shifter.

---

## 5. Bộ nhớ Flash Node (memory map)

Từ linker script [STM32F103_App.ld](../../3_node_stm32/application/STM32F103_App.ld) và `VECT_TAB_OFFSET=0x4000`:

| Vùng              | Địa chỉ bắt đầu | Kích thước | Ghi chú                       |
| ----------------- | --------------- | ---------- | ----------------------------- |
| Bootloader        | `0x0800_0000`   | 16 KB      | Nạp sẵn, không OTA            |
| Application (A)   | `0x0800_4000`   | ~48 KB     | Firmware hiện hành            |
| Application (B)   | `0x0801_0000`   | ~48 KB     | Slot dự phòng (OTA staging)   |
| Metadata / Flags  | `0x0801_FC00`   | 1 KB       | Trạng thái boot, checksum…    |

> Các giá trị trên là tham khảo theo cấu hình mặc định, hãy đối chiếu với linker script thực tế trước khi flash.

---

## 6. Công cụ nạp & debug

| Thành phần | Giao tiếp nạp       | Công cụ                    |
| ---------- | ------------------- | -------------------------- |
| ESP32 GW   | USB-UART (UART0)    | `pio run -t upload`, esptool |
| STM32 Node | SWD (PA13/PA14)     | ST-Link V2 + `stlink`      |
| Monitor    | UART0 (both)        | `pio device monitor -b 115200` |

---

## 7. Ghi chú triển khai

- Khi thay đổi chân UART của ESP32, cập nhật `UART_NODE_TX_PIN` và `UART_NODE_RX_PIN` trong [main.c](../../2_gateway_esp32/main/main.c).
- Khi đổi USART hoặc chân của STM32, cập nhật `MX_USART1_UART_Init()` trong [system_init.c](../../3_node_stm32/application/src/system_init.c) và remap GPIO tương ứng.
- Nếu chạy hai thiết bị ở hai nguồn cấp khác nhau, bắt buộc nối GND chung để tránh trôi mức logic gây lỗi UART.
