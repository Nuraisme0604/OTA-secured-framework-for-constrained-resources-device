/**
 * @file crypto_port.h
 * @brief Cryptographic primitives header for STM32
 */

#ifndef CRYPTO_PORT_H
#define CRYPTO_PORT_H

#include <stdint.h>
#include <stddef.h>
#include "../../../common/error_codes.h"
#include "../../../common/manifest_def.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Initialization
 * ============================================================================
 */

/**
 * @brief Initialize crypto subsystem
 */
void crypto_init(void);

/* ============================================================================
 * ASCON-128a Functions
 * ============================================================================
 */

/**
 * @brief Encrypt data using ASCON-128a
 */
ota_error_t crypto_ascon_encrypt(
    uint8_t* ciphertext,
    uint16_t* ciphertext_len,
    const uint8_t* key,
    const uint8_t* nonce,
    const uint8_t* plaintext,
    uint16_t plaintext_len,
    const uint8_t* ad,
    uint16_t ad_len
);

/**
 * @brief Decrypt data using ASCON-128a
 */
ota_error_t crypto_ascon_decrypt(
    uint8_t* plaintext,
    uint16_t* plaintext_len,
    const uint8_t* key,
    const uint8_t* nonce,
    const uint8_t* ciphertext,
    uint16_t ciphertext_len,
    const uint8_t* ad,
    uint16_t ad_len
);

/**
 * @brief Decrypt firmware chunk with built-in AD
 */
ota_error_t crypto_ascon_decrypt_chunk(
    uint8_t* plaintext,
    uint16_t* plaintext_len,
    const uint8_t* key,
    const uint8_t* nonce,
    const uint8_t* ciphertext,
    uint16_t ciphertext_len,
    uint16_t chunk_index,
    uint16_t total_chunks
);

/**
 * @brief Compute ASCON MAC
 */
void crypto_ascon_mac(
    uint8_t* tag,
    const uint8_t* key,
    const uint8_t* message,
    uint16_t message_len
);

/* ============================================================================
 * X25519 Functions (Key Exchange)
 * ============================================================================
 */

/**
 * @brief Generate X25519 key pair
 */
int crypto_generate_x25519_keypair(
    uint8_t* private_key,
    uint8_t* public_key
);

/**
 * @brief Derive shared secret using X25519
 */
int crypto_x25519_derive(
    uint8_t* shared_secret,
    const uint8_t* private_key,
    const uint8_t* peer_public_key
);

/**
 * @brief Derive session key from shared secret
 */
void crypto_derive_session_key(
    uint8_t* session_key,
    const uint8_t* shared_secret,
    const uint8_t* salt,
    uint16_t salt_len
);

/* ============================================================================
 * Ed25519 Functions (Signature Verification)
 * ============================================================================
 */

/**
 * @brief Verify Ed25519 signature
 */
ota_error_t crypto_verify_ed25519(
    const uint8_t* public_key,
    const uint8_t* message,
    uint32_t message_len,
    const uint8_t* signature
);

/**
 * @brief Verify manifest signature
 */
ota_error_t crypto_verify_manifest_signature(const ota_manifest_t* manifest);

/* ============================================================================
 * Hash Functions
 * ============================================================================
 */

/**
 * @brief Hash firmware at given address
 */
void crypto_hash_firmware(
    uint8_t* hash,
    uint32_t firmware_address,
    uint32_t firmware_size
);

/* ============================================================================
 * Utility Functions
 * ============================================================================
 */

/**
 * @brief Securely zero memory
 */
void crypto_zeroize(void* ptr, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* CRYPTO_PORT_H */
