/**
 * @file flash_driver.h
 * @brief Flash Driver header for STM32
 */

#ifndef FLASH_DRIVER_H
#define FLASH_DRIVER_H

#include <stdint.h>
#include <stddef.h>
#include "../../../common/error_codes.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize flash driver
 */
ota_error_t flash_init(void);

/**
 * @brief Erase flash region
 * @param address Start address (must be page-aligned)
 * @param size Number of bytes to erase (will round up to page boundary)
 */
ota_error_t flash_erase_region(uint32_t address, uint32_t size);

/**
 * @brief Write data to flash
 * @param address Destination address
 * @param data Source data
 * @param len Number of bytes to write
 */
ota_error_t flash_write(uint32_t address, const uint8_t* data, size_t len);

/**
 * @brief Read data from flash
 * @param address Source address
 * @param data Destination buffer
 * @param len Number of bytes to read
 */
ota_error_t flash_read(uint32_t address, uint8_t* data, size_t len);

/**
 * @brief Verify flash contents match expected data
 */
ota_error_t flash_verify(uint32_t address, const uint8_t* data, size_t len);

/**
 * @brief Lock flash region (write protection)
 */
ota_error_t flash_lock(uint32_t address, uint32_t size);

/**
 * @brief Unlock flash region
 */
ota_error_t flash_unlock(uint32_t address, uint32_t size);

/**
 * @brief Get flash page size
 */
uint32_t flash_get_page_size(void);

/**
 * @brief Check if address is within valid flash range
 */
int flash_is_valid_address(uint32_t address);

#ifdef __cplusplus
}
#endif

#endif /* FLASH_DRIVER_H */
