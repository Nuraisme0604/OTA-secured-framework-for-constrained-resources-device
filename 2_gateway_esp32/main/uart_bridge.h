/**
 * @file uart_bridge.h
 * @brief UART Bridge for Gateway-Node communication
 */

#ifndef UART_BRIDGE_H
#define UART_BRIDGE_H

#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "protocol_packet.h"

#ifdef __cplusplus
extern "C" {
#endif

/* UART Bridge Configuration */
typedef struct {
    uart_port_t uart_num;
    int baudrate;
    int tx_pin;
    int rx_pin;
} uart_bridge_config_t;

/* UART Bridge Handle */
typedef struct {
    uart_port_t uart_num;
    uint8_t rx_buffer[2048];
    uint16_t rx_index;
    uint8_t tx_sequence;
} uart_bridge_t;

/**
 * @brief Initialize UART bridge
 */
esp_err_t uart_bridge_init(uart_bridge_t* bridge, const uart_bridge_config_t* config);

/**
 * @brief Deinitialize UART bridge
 */
esp_err_t uart_bridge_deinit(uart_bridge_t* bridge);

/**
 * @brief Send packet to Node
 */
esp_err_t uart_bridge_send(uart_bridge_t* bridge, const packet_t* pkt);

/**
 * @brief Receive packet from Node (blocking with timeout)
 */
int uart_bridge_receive(uart_bridge_t* bridge, packet_t* pkt, TickType_t timeout);

/**
 * @brief Send raw bytes
 */
esp_err_t uart_bridge_send_raw(uart_bridge_t* bridge, const uint8_t* data, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* UART_BRIDGE_H */
