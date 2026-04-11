/**
 * @file error_codes.h
 * @brief Mã lỗi chung cho hệ thống OTA
 * 
 * Định nghĩa các mã lỗi dùng chung giữa Server, Gateway và Node.
 */

#ifndef ERROR_CODES_H
#define ERROR_CODES_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Mã lỗi hệ thống OTA
 * 
 * Phân loại:
 * - 0x00: Success
 * - 0x01-0x1F: Lỗi chung
 * - 0x20-0x3F: Lỗi xác thực (Authentication)
 * - 0x40-0x5F: Lỗi mật mã (Cryptographic)
 * - 0x60-0x7F: Lỗi truyền thông (Communication)
 * - 0x80-0x9F: Lỗi OTA (Update specific)
 * - 0xA0-0xBF: Lỗi Flash/Storage
 * - 0xC0-0xDF: Lỗi Bootloader
 * - 0xE0-0xFF: Reserved
 */
typedef enum {
    /* Success */
    OTA_OK                      = 0x00,
    
    /* General Errors (0x01-0x1F) */
    OTA_ERR_UNKNOWN             = 0x01,
    OTA_ERR_INVALID_PARAM       = 0x02,
    OTA_ERR_INVALID_STATE       = 0x03,
    OTA_ERR_TIMEOUT             = 0x04,
    OTA_ERR_BUSY                = 0x05,
    OTA_ERR_NO_MEMORY           = 0x06,
    OTA_ERR_NOT_SUPPORTED       = 0x07,
    OTA_ERR_ALREADY_EXISTS      = 0x08,
    OTA_ERR_NOT_FOUND           = 0x09,
    
    /* Authentication Errors (0x20-0x3F) */
    OTA_ERR_AUTH_FAILED         = 0x20,
    OTA_ERR_INVALID_SIGNATURE   = 0x21,
    OTA_ERR_INVALID_MANIFEST    = 0x22,
    OTA_ERR_VENDOR_MISMATCH     = 0x23,
    OTA_ERR_DEVICE_MISMATCH     = 0x24,
    OTA_ERR_SESSION_EXPIRED     = 0x25,
    OTA_ERR_CHALLENGE_FAILED    = 0x26,
    OTA_ERR_KEY_EXCHANGE_FAILED = 0x27,
    
    /* Cryptographic Errors (0x40-0x5F) */
    OTA_ERR_CRYPTO_INIT         = 0x40,
    OTA_ERR_DECRYPT_FAILED      = 0x41,
    OTA_ERR_ENCRYPT_FAILED      = 0x42,
    OTA_ERR_MAC_VERIFY_FAILED   = 0x43,
    OTA_ERR_HASH_MISMATCH       = 0x44,
    OTA_ERR_NONCE_REUSE         = 0x45,
    OTA_ERR_KEY_DERIVATION      = 0x46,
    OTA_ERR_RNG_FAILED          = 0x47,
    
    /* Communication Errors (0x60-0x7F) */
    OTA_ERR_COMM_INIT           = 0x60,
    OTA_ERR_COMM_SEND           = 0x61,
    OTA_ERR_COMM_RECV           = 0x62,
    OTA_ERR_CRC_MISMATCH        = 0x63,
    OTA_ERR_FRAME_ERROR         = 0x64,
    OTA_ERR_SEQUENCE_ERROR      = 0x65,
    OTA_ERR_PACKET_TOO_LARGE    = 0x66,
    OTA_ERR_CONNECTION_LOST     = 0x67,
    
    /* OTA Update Errors (0x80-0x9F) */
    OTA_ERR_VERSION_ROLLBACK    = 0x80,
    OTA_ERR_SIZE_MISMATCH       = 0x81,
    OTA_ERR_CHUNK_MISSING       = 0x82,
    OTA_ERR_CHUNK_DUPLICATE     = 0x83,
    OTA_ERR_UPDATE_INCOMPLETE   = 0x84,
    OTA_ERR_VERIFY_FAILED       = 0x85,
    OTA_ERR_COMMIT_FAILED       = 0x86,
    OTA_ERR_ROLLBACK_FAILED     = 0x87,
    OTA_ERR_NO_UPDATE_AVAILABLE = 0x88,
    
    /* Flash/Storage Errors (0xA0-0xBF) */
    OTA_ERR_FLASH_INIT          = 0xA0,
    OTA_ERR_FLASH_ERASE         = 0xA1,
    OTA_ERR_FLASH_WRITE         = 0xA2,
    OTA_ERR_FLASH_READ          = 0xA3,
    OTA_ERR_FLASH_VERIFY        = 0xA4,
    OTA_ERR_FLASH_LOCKED        = 0xA5,
    OTA_ERR_NO_SPACE            = 0xA6,
    OTA_ERR_PARTITION_INVALID   = 0xA7,
    
    /* Bootloader Errors (0xC0-0xDF) */
    OTA_ERR_BOOT_INVALID_IMAGE  = 0xC0,
    OTA_ERR_BOOT_SWAP_FAILED    = 0xC1,
    OTA_ERR_BOOT_HEADER_INVALID = 0xC2,
    OTA_ERR_BOOT_MAGIC_MISMATCH = 0xC3,
    OTA_ERR_BOOT_ENTRY_INVALID  = 0xC4,
    
} ota_error_t;

/**
 * @brief Chuyển mã lỗi thành chuỗi mô tả
 */
const char* ota_error_to_string(ota_error_t err);

/**
 * @brief Kiểm tra xem mã lỗi có phải là lỗi nghiêm trọng (fatal) không
 * 
 * Lỗi fatal yêu cầu reset session hoặc rollback.
 */
static inline int ota_error_is_fatal(ota_error_t err) {
    return (err >= OTA_ERR_AUTH_FAILED && err <= OTA_ERR_KEY_EXCHANGE_FAILED) ||
           (err >= OTA_ERR_CRYPTO_INIT && err <= OTA_ERR_RNG_FAILED) ||
           (err >= OTA_ERR_VERSION_ROLLBACK && err <= OTA_ERR_ROLLBACK_FAILED);
}

/**
 * @brief Kiểm tra xem lỗi có thể retry không
 */
static inline int ota_error_is_retryable(ota_error_t err) {
    return (err == OTA_ERR_TIMEOUT) ||
           (err == OTA_ERR_BUSY) ||
           (err >= OTA_ERR_COMM_INIT && err <= OTA_ERR_CONNECTION_LOST);
}

#ifdef __cplusplus
}
#endif

#endif /* ERROR_CODES_H */
