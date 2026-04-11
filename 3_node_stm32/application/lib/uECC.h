/**
 * @file uECC.h
 * @brief micro-ecc placeholder header
 * 
 * This is a placeholder header. Download the actual micro-ecc library from:
 * https://github.com/kmackay/micro-ecc
 * 
 * Or install via PlatformIO:
 * lib_deps = kmackay/micro-ecc
 */

#ifndef UECC_H
#define UECC_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* RNG function type */
typedef int (*uECC_RNG_Function)(uint8_t *dest, unsigned size);

/**
 * @brief Set RNG function for key generation
 */
void uECC_set_rng(uECC_RNG_Function rng_function);

/**
 * @brief Generate a key pair for secp256r1 curve
 * @param public_key  Output: 64 bytes (uncompressed point)
 * @param private_key Output: 32 bytes
 * @return 1 on success, 0 on failure
 */
int uECC_make_key(uint8_t *public_key, uint8_t *private_key);

/**
 * @brief Compute shared secret using ECDH
 * @param public_key  Peer's public key (64 bytes)
 * @param private_key Our private key (32 bytes)
 * @param secret      Output: shared secret (32 bytes)
 * @return 1 on success, 0 on failure
 */
int uECC_shared_secret(const uint8_t *public_key, 
                       const uint8_t *private_key,
                       uint8_t *secret);

/**
 * @brief Sign a hash using ECDSA
 * @param private_key Private key (32 bytes)
 * @param message_hash Hash of message (32 bytes)
 * @param signature   Output: signature (64 bytes)
 * @return 1 on success, 0 on failure
 */
int uECC_sign(const uint8_t *private_key,
              const uint8_t *message_hash,
              uint8_t *signature);

/**
 * @brief Verify ECDSA signature
 * @param public_key   Public key (64 bytes)
 * @param message_hash Hash of message (32 bytes)
 * @param signature    Signature (64 bytes)
 * @return 1 if valid, 0 if invalid
 */
int uECC_verify(const uint8_t *public_key,
                const uint8_t *message_hash,
                const uint8_t *signature);

#ifdef __cplusplus
}
#endif

#endif /* UECC_H */
