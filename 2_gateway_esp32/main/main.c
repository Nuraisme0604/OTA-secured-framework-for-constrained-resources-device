/**
 * @file main.c
 * @brief ESP32 Gateway - Main Application
 * 
 * Bridge giữa OTA Server (WiFi/MQTT) và STM32 Node (UART).
 * Thực hiện caching firmware và quản lý phiên OTA.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "driver/uart.h"

/* Project headers */
#include "uart_bridge.h"
#include "ota_cache.h"
// #include "protocol_parser.h"
#include "../../common/protocol_packet.h"
// #include "../../common/error_codes.h"

static const char *TAG = "GATEWAY_MAIN";

/* Configuration */
#define WIFI_SSID           CONFIG_WIFI_SSID
#define WIFI_PASS           CONFIG_WIFI_PASSWORD
#define OTA_SERVER_URL      CONFIG_OTA_SERVER_URL
#define UART_NODE_NUM       UART_NUM_1
#define UART_NODE_BAUD      115200
#define UART_NODE_TX_PIN    17
#define UART_NODE_RX_PIN    16

/* Global state */
static uart_bridge_t g_uart_bridge;
static ota_cache_t g_ota_cache;



/**
 * @brief WiFi event handler
 */
static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                               int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGI(TAG, "WiFi disconnected, reconnecting...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
    }
}


/**
 * @brief Initialize WiFi in station mode
 */
static esp_err_t wifi_init_sta(void)
{
    ESP_LOGI(TAG, "Initializing WiFi...");
    
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, &instance_got_ip));
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ESP_LOGI(TAG, "WiFi initialized, connecting to %s...", WIFI_SSID);
    return ESP_OK;
}


/**
 * @brief OTA Manager Task
 * 
 * Handles OTA workflow:
 * 1. Check for updates from server
 * 2. Download and cache firmware
 * 3. Coordinate with Node for update
 */
static void ota_manager_task(void *pvParameters)
{
    ESP_LOGI(TAG, "OTA Manager Task started");
    
    while (1) {
        /* TODO: Implement OTA check and update logic
         * 1. Poll server for available updates
         * 2. If update available:
         *    a. Download manifest
         *    b. Download firmware to cache
         *    c. Initiate handshake with Node
         *    d. Transfer firmware via UART
         *    e. Verify and commit
         */
        
        vTaskDelay(pdMS_TO_TICKS(30000));  // Check every 30s
    }
}


/**
 * @brief UART Bridge Task
 * 
 * Handles bidirectional communication with STM32 Node.
 */
static void uart_bridge_task(void *pvParameters)
{
    ESP_LOGI(TAG, "UART Bridge Task started");
    
    packet_t rx_packet;
    
    while (1) {
        /* Receive packet from Node */
        int ret = uart_bridge_receive(&g_uart_bridge, &rx_packet, pdMS_TO_TICKS(100));
        
        if (ret > 0) {
            ESP_LOGI(TAG, "Received packet type: 0x%02X, seq: %d", 
                     rx_packet.header.packet_type, rx_packet.header.sequence_num);
            
            /* Process packet based on type */
            switch (rx_packet.header.packet_type) {
                case PKT_TYPE_HELLO:
                    /* Node is requesting OTA session */
                    ESP_LOGI(TAG, "Node says hello!");
                    /* TODO: Start handshake */
                    break;
                    
                case PKT_TYPE_ACK:
                    /* Node acknowledged previous packet */
                    break;
                    
                case PKT_TYPE_FW_VERIFY:
                    /* Node finished verification */
                    break;
                    
                default:
                    ESP_LOGW(TAG, "Unknown packet type: 0x%02X", 
                             rx_packet.header.packet_type);
                    break;
            }
        }
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}


/**
 * @brief Application entry point
 */
void app_main(void)
{
    ESP_LOGI(TAG, "=== ASCON-CRA OTA Gateway ===");
    ESP_LOGI(TAG, "Firmware version: 1.0.0");
    
    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    /* Initialize UART bridge to Node */
    uart_bridge_config_t uart_cfg = {
        .uart_num = UART_NODE_NUM,
        .baudrate = UART_NODE_BAUD,
        .tx_pin = UART_NODE_TX_PIN,
        .rx_pin = UART_NODE_RX_PIN,
    };
    ESP_ERROR_CHECK(uart_bridge_init(&g_uart_bridge, &uart_cfg));
    ESP_LOGI(TAG, "UART bridge initialized");
    
    /* Initialize OTA cache */
    ESP_ERROR_CHECK(ota_cache_init(&g_ota_cache));
    ESP_LOGI(TAG, "OTA cache initialized");
    
    /* Initialize WiFi */
    ESP_ERROR_CHECK(wifi_init_sta());
    
    /* Create tasks */
    xTaskCreate(ota_manager_task, "ota_mgr", 4096, NULL, 5, NULL);
    xTaskCreate(uart_bridge_task, "uart_bridge", 4096, NULL, 10, NULL);
    
    ESP_LOGI(TAG, "Gateway started successfully");
}
