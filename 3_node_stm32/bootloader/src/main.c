/**
 * @file main.c
 * @brief STM32 OTA Bootloader - Root of Trust
 * 
 * Bootloader responsibilities:
 * 1. Verify firmware signature before jumping
 * 2. Manage A/B partition swapping
 * 3. Anti-rollback protection
 * 4. Watchdog for failed updates
 */

#include "stm32f1xx_hal.h"
#include <string.h>
#include <stdint.h>

/* Project headers - common definitions */
#include "manifest_def.h"
#include "error_codes.h"

/* ============================================================================
 * Flash Memory Map for STM32F103C8 (64KB Flash)
 * ============================================================================
 * 
 * 0x08000000 - 0x08002FFF : Bootloader (12KB)
 * 0x08003000 - 0x08003FFF : Metadata (4KB) - Manifest + Boot flags
 * 0x08004000 - 0x0800FFFF : Application (48KB)
 * 
 * Hoặc với A/B partitioning (128KB Flash - STM32F103RCT6):
 * 0x08000000 - 0x08003FFF : Bootloader (16KB)
 * 0x08004000 - 0x08004FFF : Metadata (4KB)
 * 0x08005000 - 0x0800AFFF : Slot A (24KB)
 * 0x0800B000 - 0x0800FFFF : Slot B (20KB)
 * ============================================================================
 */

#define BOOTLOADER_START    0x08000000
#define METADATA_START      0x08003000
#define APP_SLOT_A_START    0x08004000
#define APP_SLOT_B_START    0x0800A000  /* For A/B partitioning */

#define METADATA_SIZE       0x1000      /* 4KB */
#define APP_MAX_SIZE        0x6000      /* 24KB per slot */

/* Boot flags */
#define BOOT_FLAG_MAGIC     0xB007F1A6
#define BOOT_FLAG_SLOT_A    0x00
#define BOOT_FLAG_SLOT_B    0x01
#define BOOT_FLAG_PENDING   0x02
#define BOOT_FLAG_VERIFIED  0x04

/* Metadata structure stored in Flash */
typedef struct {
    uint32_t magic;                     /* BOOT_FLAG_MAGIC */
    uint8_t  active_slot;               /* Current active slot (A or B) */
    uint8_t  pending_slot;              /* Slot waiting for verification */
    uint8_t  boot_attempts;             /* Failed boot counter */
    uint8_t  flags;                     /* Boot flags */
    uint32_t security_counter;          /* Anti-rollback counter */
    ota_manifest_t manifest_a;          /* Manifest for Slot A */
    ota_manifest_t manifest_b;          /* Manifest for Slot B */
    uint32_t crc32;                     /* CRC32 of this structure */
} boot_metadata_t;

/* Vendor public key for signature verification (HARDCODED - Root of Trust) */
static const uint8_t VENDOR_PUBLIC_KEY[32] = {
    /* TODO: Replace with actual vendor Ed25519 public key */
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

/* Maximum boot attempts before rollback */
#define MAX_BOOT_ATTEMPTS   3

/* ============================================================================
 * Function Prototypes
 * ============================================================================
 */

static void system_init(void);
static void jump_to_application(uint32_t app_address);
static ota_error_t verify_firmware(const ota_manifest_t* manifest, uint32_t app_address);
static ota_error_t verify_signature(const ota_manifest_t* manifest);
static uint32_t calculate_crc32(const uint8_t* data, uint32_t length);
static boot_metadata_t* get_metadata(void);
static void update_boot_attempts(uint8_t attempts);


/* ============================================================================
 * Main Entry Point
 * ============================================================================
 */

int main(void)
{
    /* Initialize HAL */
    HAL_Init();
    system_init();
    
    /* Get boot metadata */
    boot_metadata_t* meta = get_metadata();
    
    /* Validate metadata */
    if (meta->magic != BOOT_FLAG_MAGIC) {
        /* First boot or corrupted metadata - initialize */
        /* TODO: Initialize with default values */
    }
    
    /* Check if there's a pending update */
    if (meta->flags & BOOT_FLAG_PENDING) {
        /* Increment boot attempt counter */
        meta->boot_attempts++;
        update_boot_attempts(meta->boot_attempts);
        
        if (meta->boot_attempts >= MAX_BOOT_ATTEMPTS) {
            /* Too many failed attempts - rollback */
            /* TODO: Rollback to previous slot */
            meta->flags &= ~BOOT_FLAG_PENDING;
            meta->boot_attempts = 0;
        }
    }
    
    /* Determine which slot to boot */
    uint32_t app_address;
    const ota_manifest_t* manifest;
    
    if (meta->active_slot == BOOT_FLAG_SLOT_A) {
        app_address = APP_SLOT_A_START;
        manifest = &meta->manifest_a;
    } else {
        app_address = APP_SLOT_B_START;
        manifest = &meta->manifest_b;
    }
    
    /* Verify firmware before jumping */
    ota_error_t err = verify_firmware(manifest, app_address);
    
    if (err != OTA_OK) {
        /* Verification failed - try other slot */
        if (meta->active_slot == BOOT_FLAG_SLOT_A) {
            app_address = APP_SLOT_B_START;
            manifest = &meta->manifest_b;
        } else {
            app_address = APP_SLOT_A_START;
            manifest = &meta->manifest_a;
        }
        
        err = verify_firmware(manifest, app_address);
        if (err != OTA_OK) {
            /* Both slots invalid - halt */
            while (1) {
                /* TODO: Signal error via LED */
                HAL_Delay(500);
            }
        }
    }
    
    /* Clear pending flag if verification succeeded */
    if (meta->flags & BOOT_FLAG_PENDING) {
        meta->flags &= ~BOOT_FLAG_PENDING;
        meta->flags |= BOOT_FLAG_VERIFIED;
        meta->boot_attempts = 0;
        /* TODO: Save to flash */
    }
    
    /* Jump to application */
    jump_to_application(app_address);
    
    /* Should never reach here */
    while (1);
}


/* ============================================================================
 * System Initialization
 * ============================================================================
 */

static void system_init(void)
{
    /* Configure system clock */
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
    
    /* Use internal HSI oscillator for bootloader (fast startup) */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);
    
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0);
}


/* ============================================================================
 * Jump to Application
 * ============================================================================
 */

static void jump_to_application(uint32_t app_address)
{
    /* Disable all interrupts */
    __disable_irq();
    
    /* Get application's stack pointer and reset handler */
    uint32_t app_stack = *((volatile uint32_t*)app_address);
    uint32_t app_reset = *((volatile uint32_t*)(app_address + 4));
    
    /* Validate stack pointer (must be in RAM) */
    if ((app_stack & 0x2FFE0000) != 0x20000000) {
        /* Invalid stack pointer */
        __enable_irq();
        return;
    }
    
    /* Deinitialize HAL */
    HAL_DeInit();
    
    /* Reset all peripherals */
    __HAL_RCC_APB1_FORCE_RESET();
    __HAL_RCC_APB1_RELEASE_RESET();
    __HAL_RCC_APB2_FORCE_RESET();
    __HAL_RCC_APB2_RELEASE_RESET();
    
    /* Set vector table offset */
    SCB->VTOR = app_address;
    
    /* Set stack pointer */
    __set_MSP(app_stack);
    
    /* Jump to application */
    void (*app_entry)(void) = (void (*)(void))app_reset;
    app_entry();
}


/* ============================================================================
 * Firmware Verification
 * ============================================================================
 */

static ota_error_t verify_firmware(const ota_manifest_t* manifest, uint32_t app_address)
{
    /* Check manifest magic */
    if (!manifest_is_valid(manifest)) {
        return OTA_ERR_INVALID_MANIFEST;
    }
    
    /* Anti-rollback check */
    boot_metadata_t* meta = get_metadata();
    if (manifest->security_version < meta->security_counter) {
        return OTA_ERR_VERSION_ROLLBACK;
    }
    
    /* Verify signature */
    ota_error_t err = verify_signature(manifest);
    if (err != OTA_OK) {
        return err;
    }
    
    /* Verify firmware hash */
    /* TODO: Calculate hash of firmware at app_address and compare with manifest->fw_hash */
    
    return OTA_OK;
}


static ota_error_t verify_signature(const ota_manifest_t* manifest)
{
    /* TODO: Implement Ed25519 signature verification
     * 1. Extract signed data (manifest without signature)
     * 2. Verify signature using VENDOR_PUBLIC_KEY
     */
    
    /* Placeholder - always pass for testing */
    (void)manifest;
    (void)VENDOR_PUBLIC_KEY;
    
    return OTA_OK;
}


/* ============================================================================
 * Utility Functions
 * ============================================================================
 */

static boot_metadata_t* get_metadata(void)
{
    return (boot_metadata_t*)METADATA_START;
}


static void update_boot_attempts(uint8_t attempts)
{
    /* TODO: Update boot attempts in Flash
     * Note: STM32F1 requires erasing full page before writing
     * Consider using a separate small area for frequently updated counters
     */
    (void)attempts;
}


static uint32_t calculate_crc32(const uint8_t* data, uint32_t length)
{
    /* TODO: Implement CRC32 or use hardware CRC if available */
    (void)data;
    (void)length;
    return 0;
}
