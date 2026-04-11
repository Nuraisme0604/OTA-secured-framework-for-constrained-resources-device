/**
 * @file ota_handler.h
 * @brief OTA Handler header for STM32
 */

#ifndef OTA_HANDLER_H
#define OTA_HANDLER_H

#include <stdint.h>
#include "../../../common/error_codes.h"
#include "../../../common/protocol_packet.h"
#include "../../../common/manifest_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize OTA handler
 */
void ota_handler_init(void);

/**
 * @brief Start OTA session
 */
ota_error_t ota_start_session(void);

/**
 * @brief Process received packet
 */
ota_error_t ota_process_packet(const packet_t* pkt);

/**
 * @brief Get current OTA progress (0-100)
 */
uint8_t ota_get_progress(void);

/**
 * @brief Check if OTA is in progress
 */
int ota_is_active(void);

/**
 * @brief Abort current OTA session
 */
void ota_abort(void);

/* External helper functions (to be implemented by platform) */
uint32_t get_device_id(void);
uint32_t get_current_fw_version(void);
uint32_t get_security_counter(void);
uint32_t get_inactive_slot_address(void);

#ifdef __cplusplus
}
#endif

#endif /* OTA_HANDLER_H */
