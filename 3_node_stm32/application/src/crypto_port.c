/**
 * @file crypto_port.c
 * @brief Cryptographic primitives ported for STM32
 * 
 * Provides wrappers around crypto libraries:
 * - ASCON-128a (from ascon-c library)
 * - X25519 (from micro-ecc)
 * - Ed25519 (from micro-ecc or monocypher)
 */

#include "crypto_port.h"
#include "stm32f1xx_hal.h"  /* Provides SysTick and other CMSIS definitions */
#include <string.h>

/* Include ASCON library from ascon-c-lib 
 * Note: Copy the required files from e:\NCKH\ascon-c-lib\crypto_aead\ascon128av12
 */
#include "ascon.h"
// #include "crypto_aead.h"

/* Include micro-ecc for ECC operations */
#include "uECC.h"

/* Vendor public key for signature verification */
extern const uint8_t VENDOR_PUBLIC_KEY[32];


/* ============================================================================
 * Initialization
 * ============================================================================
 */

static int rng_function(uint8_t *dest, unsigned size)
{
    /* Use hardware RNG if available (STM32F4/L4), otherwise use ADC noise */
    /* For STM32F1, we need to use software PRNG seeded from ADC noise */
    
    /* TODO: Implement proper hardware RNG or PRNG */
    /* Placeholder: NOT SECURE - use only for testing */
    for (unsigned i = 0; i < size; i++) {
        dest[i] = (uint8_t)(SysTick->VAL ^ (i * 17));
    }
    return 1;
}


void crypto_init(void)
{
    /* Set RNG function for micro-ecc */
    /* uECC_set_rng(rng_function); -> Causing link error with default lib config */
}


/* ============================================================================
 * ASCON Functions
 * ============================================================================
 */

ota_error_t crypto_ascon_encrypt(
    uint8_t* ciphertext,
    uint16_t* ciphertext_len,
    const uint8_t* key,
    const uint8_t* nonce,
    const uint8_t* plaintext,
    uint16_t plaintext_len,
    const uint8_t* ad,
    uint16_t ad_len)
{
    /* ASCON-128a encryption */
    /* tag is appended to ciphertext */
    uint8_t* tag = ciphertext + plaintext_len;
    
    /* 
     * ascon_aead_encrypt signature:
     * int ascon_aead_encrypt(uint8_t* t, uint8_t* c, const uint8_t* m, uint64_t mlen,
     *                        const uint8_t* ad, uint64_t adlen, const uint8_t* npub,
     *                        const uint8_t* k);
     */
    ascon_aead_encrypt(
        tag,                        /* output: tag (16 bytes) */
        ciphertext,                 /* output: ciphertext */
        plaintext, plaintext_len,   /* input: plaintext */
        ad, ad_len,                 /* associated data */
        nonce,                      /* public nonce */
        key                         /* key */
    );
    
    *ciphertext_len = plaintext_len + 16;
    return OTA_OK;
}


ota_error_t crypto_ascon_decrypt(
    uint8_t* plaintext,
    uint16_t* plaintext_len,
    const uint8_t* key,
    const uint8_t* nonce,
    const uint8_t* ciphertext,
    uint16_t ciphertext_len,
    const uint8_t* ad,
    uint16_t ad_len)
{
    if (ciphertext_len < 16) return OTA_ERR_FRAME_ERROR;
    
    uint64_t clen = ciphertext_len - 16;
    const uint8_t* tag = ciphertext + clen;
    
    /* ASCON-128a decryption */
    int ret = ascon_aead_decrypt(
        plaintext,                  /* output: plaintext */
        tag,                        /* input: tag */
        ciphertext, clen,           /* input: ciphertext */
        ad, ad_len,                 /* associated data */
        nonce,                      /* public nonce */
        key                         /* key */
    );
    
    *plaintext_len = (uint16_t)clen;
    return (ret == 0) ? OTA_OK : OTA_ERR_MAC_VERIFY_FAILED;
}


ota_error_t crypto_ascon_decrypt_chunk(
    uint8_t* plaintext,
    uint16_t* plaintext_len,
    const uint8_t* key,
    const uint8_t* nonce,
    const uint8_t* ciphertext,
    uint16_t ciphertext_len,
    uint16_t chunk_index,
    uint16_t total_chunks)
{
    /* Build associated data for chunk authentication */
    uint8_t ad[4];
    ad[0] = chunk_index & 0xFF;
    ad[1] = (chunk_index >> 8) & 0xFF;
    ad[2] = total_chunks & 0xFF;
    ad[3] = (total_chunks >> 8) & 0xFF;
    
    return crypto_ascon_decrypt(
        plaintext, plaintext_len,
        key, nonce,
        ciphertext, ciphertext_len,
        ad, 4
    );
}


void crypto_ascon_mac(
    uint8_t* tag,
    const uint8_t* key,
    const uint8_t* message,
    uint16_t message_len)
{
    /* Use ASCON in authentication-only mode (empty plaintext) */
    uint8_t dummy_nonce[16] = {0};
    uint8_t dummy_cipher[1]; /* Placeholder for 0-length ciphertext */
    
    ascon_aead_encrypt(
        tag,                        /* output: tag */
        dummy_cipher,               /* output: ciphertext (empty) */
        NULL, 0,                    /* input: plaintext (empty) */
        message, message_len,       /* associated data */
        dummy_nonce,                /* nonce */
        key                         /* key */
    );
}


/* ============================================================================
 * X25519 Functions (Key Exchange)
 * ============================================================================
 */

int crypto_generate_x25519_keypair(
    uint8_t* private_key,
    uint8_t* public_key)
{
    /* Generate random private key */
    if (!rng_function(private_key, 32)) {
        return -1;
    }
    
    /* Clamp private key per RFC 7748 */
    private_key[0] &= 248;
    private_key[31] &= 127;
    private_key[31] |= 64;
    
    /* Compute public key */
    /* Note: micro-ecc uses curve25519_donna or similar */
    /* TODO: Use actual X25519 implementation */
    
    return 0;
}


int crypto_x25519_derive(
    uint8_t* shared_secret,
    const uint8_t* private_key,
    const uint8_t* peer_public_key)
{
    /* Perform X25519 key agreement */
    /* TODO: Use actual X25519 implementation */
    
    /* Placeholder: XOR for testing only */
    for (int i = 0; i < 32; i++) {
        shared_secret[i] = private_key[i] ^ peer_public_key[i];
    }
    
    return 0;
}


void crypto_derive_session_key(
    uint8_t* session_key,
    const uint8_t* shared_secret,
    const uint8_t* salt,
    uint16_t salt_len)
{
    /* Simple key derivation using ASCON in hash mode */
    /* TODO: Use proper HKDF or ASCON-XOF */
    
    uint8_t input[64];
    memcpy(input, shared_secret, 32);
    
    if (salt_len > 0 && salt_len <= 32) {
        memcpy(input + 32, salt, salt_len);
    }
    
    /* Use ASCON-Hash to derive session key */
    /* Simplified: just XOR and truncate for now */
    for (int i = 0; i < 16; i++) {
        session_key[i] = input[i] ^ input[i + 16] ^ input[i + 32];
    }
}


/* ============================================================================
 * Ed25519 Functions (Signature Verification)
 * ============================================================================
 */

ota_error_t crypto_verify_ed25519(
    const uint8_t* public_key,
    const uint8_t* message,
    uint32_t message_len,
    const uint8_t* signature)
{
    /* TODO: Implement Ed25519 verification using monocypher or similar
     * 
     * For now, return OK for testing (NOT SECURE)
     */
    (void)public_key;
    (void)message;
    (void)message_len;
    (void)signature;
    
    return OTA_OK;
}


ota_error_t crypto_verify_manifest_signature(const ota_manifest_t* manifest)
{
    /* Verify Ed25519 signature over manifest (excluding signature field) */
    return crypto_verify_ed25519(
        VENDOR_PUBLIC_KEY,
        (const uint8_t*)manifest,
        MANIFEST_SIGNED_SIZE,
        manifest->signature
    );
}


/* ============================================================================
 * Hash Functions
 * ============================================================================
 */

void crypto_hash_firmware(
    uint8_t* hash,
    uint32_t firmware_address,
    uint32_t firmware_size)
{
    /* Hash firmware in flash using ASCON-Hash or SHA-256 */
    /* TODO: Implement incremental hashing for large firmware */
    
    /* Placeholder: NOT A REAL HASH */
    const uint8_t* fw = (const uint8_t*)firmware_address;
    
    /* Simple checksum for testing */
    memset(hash, 0, 32);
    for (uint32_t i = 0; i < firmware_size; i++) {
        hash[i % 32] ^= fw[i];
    }
}


/* ============================================================================
 * Secure Memory Operations
 * ============================================================================
 */

void crypto_zeroize(void* ptr, size_t len)
{
    /* Secure memory zeroing to prevent compiler optimization */
    volatile uint8_t* p = (volatile uint8_t*)ptr;
    while (len--) {
        *p++ = 0;
    }
}
