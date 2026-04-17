/**
 * @file uart_bridge.c
 * @brief UART Bridge Implementation
 */

#include "uart_bridge.h"
#include "protocol_parser.h"
#include <string.h>

esp_err_t uart_bridge_init(uart_bridge_t* bridge, const uart_bridge_config_t* config) {
    if (!bridge || !config) return ESP_ERR_INVALID_ARG;
    
    bridge->uart_num = config->uart_num;
    bridge->rx_index = 0;
    bridge->tx_sequence = 0;
    
    uart_config_t uart_config = {
        .baud_rate = config->baudrate,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    
    ESP_ERROR_CHECK(uart_driver_install(bridge->uart_num, 2048, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(bridge->uart_num, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(bridge->uart_num, config->tx_pin, config->rx_pin, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    
    return ESP_OK;
}

esp_err_t uart_bridge_deinit(uart_bridge_t* bridge) {
    if (!bridge) return ESP_ERR_INVALID_ARG;
    return uart_driver_delete(bridge->uart_num);
}

esp_err_t uart_bridge_send(uart_bridge_t* bridge, const packet_t* pkt) {
    if (!bridge || !pkt) return ESP_ERR_INVALID_ARG;
    
    uint8_t buffer[MAX_FRAME_SIZE];
    int len = protocol_serialize(pkt, buffer, sizeof(buffer));
    
    if (len > 0) {
        int txBytes = uart_write_bytes(bridge->uart_num, buffer, len);
        return (txBytes == len) ? ESP_OK : ESP_FAIL;
    }
    
    return ESP_FAIL;
}

int uart_bridge_receive(uart_bridge_t* bridge, packet_t* pkt, TickType_t timeout) {
    if (!bridge || !pkt) return -1;
    
    /* Simple implementation: Read byte by byte or block and feed parser */
    /* For efficiency, we should read blocks */
    
    uint8_t data[64];
    protocol_parser_t parser;
    protocol_parser_init(&parser);
    
    TickType_t start_tick = xTaskGetTickCount();
    
    while ((xTaskGetTickCount() - start_tick) < timeout) {
        int len = uart_read_bytes(bridge->uart_num, data, sizeof(data), pdMS_TO_TICKS(10));
        if (len > 0) {
            for (int i = 0; i < len; i++) {
                int ret = protocol_parser_feed(&parser, data[i]);
                if (ret == 1) {
                    /* Packet complete */
                    *pkt = parser.packet;
                    return 1;
                } else if (ret < 0) {
                    /* Error, reset parser */
                    protocol_parser_reset(&parser);
                }
            }
        }
    }
    
    return 0; /* Timeout */
}

esp_err_t uart_bridge_send_raw(uart_bridge_t* bridge, const uint8_t* data, size_t len) {
    if (!bridge || !data) return ESP_ERR_INVALID_ARG;
    uart_write_bytes(bridge->uart_num, data, len);
    return ESP_OK;
}
