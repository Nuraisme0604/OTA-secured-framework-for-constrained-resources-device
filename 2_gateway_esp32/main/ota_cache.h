/**
 * @file ota_cache.h
 * @brief OTA Firmware Cache for ESP32 Gateway
 * 
 * Caches downloaded firmware in SPIFFS/LittleFS or external flash
 */

#ifndef OTA_CACHE_H
#define OTA_CACHE_H

#include "esp_err.h"
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Maximum cached firmware size (e.g., 256KB) */
#define OTA_CACHE_MAX_SIZE      (256 * 1024)

/* Cache status */
typedef enum {
    CACHE_STATUS_EMPTY,
    CACHE_STATUS_PARTIAL,
    CACHE_STATUS_COMPLETE,
    CACHE_STATUS_VERIFIED,
} ota_cache_status_t;

/* OTA Cache Handle */
typedef struct {
    ota_cache_status_t status;
    uint32_t total_size;
    uint32_t cached_size;
    uint16_t total_chunks;
    uint16_t cached_chunks;
    uint8_t* chunk_bitmap;      /* Bitmap of received chunks */
    char firmware_path[64];     /* Path to cached firmware file */
    char manifest_path[64];     /* Path to cached manifest */
} ota_cache_t;

/**
 * @brief Initialize OTA cache
 */
esp_err_t ota_cache_init(ota_cache_t* cache);

/**
 * @brief Deinitialize OTA cache
 */
esp_err_t ota_cache_deinit(ota_cache_t* cache);

/**
 * @brief Start caching a new firmware
 */
esp_err_t ota_cache_start(ota_cache_t* cache, uint32_t total_size, uint16_t total_chunks);

/**
 * @brief Write a firmware chunk to cache
 */
esp_err_t ota_cache_write_chunk(ota_cache_t* cache, uint16_t chunk_index, 
                                 const uint8_t* data, size_t len);

/**
 * @brief Read a firmware chunk from cache
 */
esp_err_t ota_cache_read_chunk(ota_cache_t* cache, uint16_t chunk_index,
                                uint8_t* data, size_t* len);

/**
 * @brief Check if a chunk is cached
 */
bool ota_cache_has_chunk(ota_cache_t* cache, uint16_t chunk_index);

/**
 * @brief Get number of missing chunks
 */
uint16_t ota_cache_missing_chunks(ota_cache_t* cache);

/**
 * @brief Clear the cache
 */
esp_err_t ota_cache_clear(ota_cache_t* cache);

/**
 * @brief Get cache status
 */
ota_cache_status_t ota_cache_get_status(ota_cache_t* cache);

#ifdef __cplusplus
}
#endif

#endif /* OTA_CACHE_H */
