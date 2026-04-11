/**
 * @file flash_driver.c
 * @brief STM32F103 Flash Driver for OTA
 */

#include "flash_driver.h"
#include "stm32f1xx_hal.h"
#include <string.h>

/* STM32F103 Page Size is 1KB (Medium Density) */
#undef FLASH_PAGE_SIZE
#define FLASH_PAGE_SIZE 1024

ota_error_t flash_erase_region(uint32_t start_address, uint32_t size)
{
    /* Validate alignment */
    if (start_address % FLASH_PAGE_SIZE != 0) {
        return OTA_ERR_FLASH_WRITE;
    }
    
    HAL_StatusTypeDef status;
    uint32_t page_error = 0;
    FLASH_EraseInitTypeDef erase_init;
    
    erase_init.TypeErase = FLASH_TYPEERASE_PAGES;
    erase_init.PageAddress = start_address;
    erase_init.NbPages = (size + FLASH_PAGE_SIZE - 1) / FLASH_PAGE_SIZE;
    erase_init.Banks = FLASH_BANK_1;
    
    HAL_FLASH_Unlock();
    
    status = HAL_FLASHEx_Erase(&erase_init, &page_error);
    
    HAL_FLASH_Lock();
    
    return (status == HAL_OK) ? OTA_OK : OTA_ERR_FLASH_ERASE;
}

ota_error_t flash_write(uint32_t address, const uint8_t* data, size_t len)
{
    HAL_StatusTypeDef status = HAL_OK;
    
    HAL_FLASH_Unlock();
    
    for (uint32_t i = 0; i < len; i += 4) {
        /* Read 4 bytes as word (Little Endian) */
        uint32_t word = 0;
        
        /* Handle partial words at the end */
        if (i + 4 <= len) {
            memcpy(&word, data + i, 4);
        } else {
            memcpy(&word, data + i, len - i);
            /* Pad with 0xFF (erased state) if needed, though STM32 writes 0s usually */
            /* Actually better to pad with existing data if we were modifying, but here we overwrite */
        }
        
        status = HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, address + i, word);
        if (status != HAL_OK) {
            break;
        }
    }
    
    HAL_FLASH_Lock();
    
    return (status == HAL_OK) ? OTA_OK : OTA_ERR_FLASH_WRITE;
}

ota_error_t flash_read(uint32_t address, uint8_t* data, size_t len)
{
    memcpy(data, (void*)address, len);
    return OTA_OK;
}
