/**
 * @file ota_cache.c
 * @brief OTA Cache Implementation (Stub/RAM-based for now)
 */

#include "ota_cache.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "OTA_CACHE";

/* Simple RAM buffer for testing (limited size) */
/* In production, use partition API */
#define STUB_CACHE_SIZE (16 * 1024) 
static uint8_t g_ram_cache[STUB_CACHE_SIZE];

esp_err_t ota_cache_init(ota_cache_t* cache) {
    if (!cache) return ESP_ERR_INVALID_ARG;
    memset(cache, 0, sizeof(ota_cache_t));
    cache->status = CACHE_STATUS_EMPTY;
    ESP_LOGI(TAG, "OTA Cache Initialized (RAM Stub Mode)");
    return ESP_OK;
}

esp_err_t ota_cache_deinit(ota_cache_t* cache) {
    return ESP_OK;
}

esp_err_t ota_cache_start(ota_cache_t* cache, uint32_t total_size, uint16_t total_chunks) {
    if (!cache) return ESP_ERR_INVALID_ARG;
    
    if (total_size > STUB_CACHE_SIZE) {
        ESP_LOGW(TAG, "Firmware too large for RAM stub cache! (%d > %d)", total_size, STUB_CACHE_SIZE);
        /* Allowing it to proceed but writes might fail or overwrite */
    }
    
    cache->total_size = total_size;
    cache->total_chunks = total_chunks;
    cache->cached_size = 0;
    cache->cached_chunks = 0;
    cache->status = CACHE_STATUS_PARTIAL;
    
    memset(g_ram_cache, 0xFF, STUB_CACHE_SIZE);
    
    ESP_LOGI(TAG, "Starting Cache: %d bytes, %d chunks", total_size, total_chunks);
    return ESP_OK;
}

esp_err_t ota_cache_write_chunk(ota_cache_t* cache, uint16_t chunk_index, 
                                 const uint8_t* data, size_t len) {
    if (!cache || !data) return ESP_ERR_INVALID_ARG;
    
    /* Stub: Just copy to RAM if fits */
    uint32_t offset = chunk_index * 1024; /* Assuming 1KB chunks */
    if (offset + len <= STUB_CACHE_SIZE) {
        memcpy(&g_ram_cache[offset], data, len);
    }
    
    cache->cached_chunks++;
    cache->cached_size += len;
    
    /* Update bitmap (not implemented in stub) */
    
    ESP_LOGI(TAG, "Wrote Chunk %d (%d bytes)", chunk_index, len);
    
    if (cache->cached_chunks >= cache->total_chunks) {
        cache->status = CACHE_STATUS_COMPLETE;
        ESP_LOGI(TAG, "Cache Complete!");
    }
    
    return ESP_OK;
}

esp_err_t ota_cache_read_chunk(ota_cache_t* cache, uint16_t chunk_index,
                                uint8_t* data, size_t* len) {
    if (!cache || !data || !len) return ESP_ERR_INVALID_ARG;
    
    uint32_t offset = chunk_index * 1024;
    size_t chunk_size = 1024;
    
    /* Clamp last chunk size logic needed here */
    
    if (offset + chunk_size <= STUB_CACHE_SIZE) {
        memcpy(data, &g_ram_cache[offset], chunk_size);
        *len = chunk_size;
    } else {
        /* Return empty or pattern */
        memset(data, 0, chunk_size);
        *len = chunk_size;
    }
    
    return ESP_OK;
}

bool ota_cache_has_chunk(ota_cache_t* cache, uint16_t chunk_index) {
    /* Stub always returns true for now */
    return true;
}

uint16_t ota_cache_missing_chunks(ota_cache_t* cache) {
    if (cache->status == CACHE_STATUS_COMPLETE) return 0;
    return cache->total_chunks - cache->cached_chunks;
}

esp_err_t ota_cache_clear(ota_cache_t* cache) {
    cache->status = CACHE_STATUS_EMPTY;
    cache->cached_size = 0;
    cache->cached_chunks = 0;
    return ESP_OK;
}

ota_cache_status_t ota_cache_get_status(ota_cache_t* cache) {
    return cache->status;
}
