/**
 * @file manifest_def.h
 * @brief Cấu trúc Manifest cho OTA Update
 * 
 * Định nghĩa cấu trúc dữ liệu Manifest dùng chung giữa Server, Gateway và Node.
 * Sử dụng #pragma pack(push, 1) để đảm bảo không có padding trên các kiến trúc khác nhau.
 */

#ifndef MANIFEST_DEF_H
#define MANIFEST_DEF_H

#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Kích thước các trường cố định */
#define MANIFEST_VERSION_MAJOR  1
#define MANIFEST_VERSION_MINOR  0

#define FW_HASH_SIZE            32   /* SHA-256 hoặc ASCON-Hash */
#define SIGNATURE_SIZE          64   /* Ed25519 signature */
#define NONCE_SIZE              16   /* ASCON nonce (128-bit) */
#define VENDOR_ID_SIZE          4    /* Vendor identifier */
#define DEVICE_CLASS_SIZE       2    /* Device class (e.g., STM32F1, ESP32) */

/* Magic number để nhận dạng Manifest hợp lệ */
#define MANIFEST_MAGIC          0x4F54414D  /* "MOTA" in little-endian */

#pragma pack(push, 1)

/**
 * @brief Cấu trúc Manifest cho OTA firmware
 * 
 * Thứ tự các trường được sắp xếp để tối ưu:
 * 1. Magic + Version ở đầu để quick-check
 * 2. Metadata (vendor, device, firmware info) ở giữa
 * 3. Crypto fields (hash, nonce) 
 * 4. Signature ở cuối để dễ verify (chỉ cần hash từ byte 0 đến trước signature)
 */
typedef struct {
    /* Header - 8 bytes */
    uint32_t magic;                     /* Magic number: 0x4F54414D ("MOTA") */
    uint8_t  version_major;             /* Manifest format version major */
    uint8_t  version_minor;             /* Manifest format version minor */
    uint16_t header_size;               /* Size of this manifest struct */
    
    /* Vendor & Device Info - 10 bytes */
    uint8_t  vendor_id[VENDOR_ID_SIZE]; /* Unique vendor identifier */
    uint8_t  device_class[DEVICE_CLASS_SIZE]; /* Target device class */
    uint32_t device_id;                 /* Target device ID (0 = broadcast) */
    
    /* Firmware Metadata - 16 bytes */
    uint32_t fw_version;                /* Firmware version (semantic: major.minor.patch.build) */
    uint32_t fw_size;                   /* Firmware size in bytes */
    uint32_t fw_entry_point;            /* Entry point address (for bootloader) */
    uint16_t chunk_size;                /* Size of each chunk for transfer */
    uint16_t total_chunks;              /* Total number of chunks */
    
    /* Anti-rollback - 8 bytes */
    uint32_t security_version;          /* Security counter (anti-rollback) */
    uint32_t build_timestamp;           /* Unix timestamp of build */
    
    /* Crypto Fields - 48 bytes */
    uint8_t  fw_hash[FW_HASH_SIZE];     /* Hash of plaintext firmware */
    uint8_t  nonce_base[NONCE_SIZE];    /* Base nonce for ASCON encryption */
    
    /* Signature - 64 bytes (MUST be last) */
    uint8_t  signature[SIGNATURE_SIZE]; /* Ed25519 signature over all above fields */
    
} ota_manifest_t;

#pragma pack(pop)

/* Kích thước phần cần ký (không bao gồm signature) */
#define MANIFEST_SIGNED_SIZE    (sizeof(ota_manifest_t) - SIGNATURE_SIZE)

/* Kiểm tra tính hợp lệ của Manifest */
static inline int manifest_is_valid(const ota_manifest_t* m) {
    return (m != NULL) && 
           (m->magic == MANIFEST_MAGIC) &&
           (m->version_major == MANIFEST_VERSION_MAJOR);
}

#ifdef __cplusplus
}
#endif

#endif /* MANIFEST_DEF_H */
