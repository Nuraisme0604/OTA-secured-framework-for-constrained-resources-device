/**
 * @file ota_handler.c
 * @brief STM32 OTA Handler - State Machine for OTA Updates
 * 
 * Implements the OTA protocol state machine:
 * 1. Handshake (CRA authentication)
 * 2. Manifest reception and verification
 * 3. Firmware download and decryption
 * 4. Verification and commit
 */

#include "ota_handler.h"
#include "crypto_port.h"
#include "flash_driver.h"
#include "../../../common/manifest_def.h"
#include "../../../common/protocol_packet.h"
#include "../../../common/error_codes.h"

#include <string.h>
#include "stm32f1xx_hal.h"  /* For NVIC_SystemReset() */

/* ============================================================================
 * OTA State Machine
 * ============================================================================
 */

typedef enum {
    OTA_STATE_IDLE,
    OTA_STATE_HANDSHAKE,
    OTA_STATE_WAIT_CHALLENGE,
    OTA_STATE_WAIT_SESSION_KEY,
    OTA_STATE_WAIT_MANIFEST,
    OTA_STATE_DOWNLOADING,
    OTA_STATE_VERIFYING,
    OTA_STATE_COMMITTING,
    OTA_STATE_ERROR,
} ota_state_t;

typedef struct {
    ota_state_t state;
    
    /* Session data */
    uint8_t session_key[16];            /* ASCON encryption key */
    uint8_t nonce_base[16];             /* Base nonce from manifest */
    uint8_t device_private_key[32];     /* Ephemeral X25519 private key */
    uint8_t device_public_key[32];      /* Ephemeral X25519 public key */
    uint8_t server_public_key[32];      /* Server's X25519 public key */
    
    /* Manifest data */
    ota_manifest_t current_manifest;
    
    /* Download progress */
    uint16_t expected_chunks;
    uint16_t received_chunks;
    uint32_t bytes_written;
    uint32_t target_address;            /* Flash address for new firmware */
    
    /* Error handling */
    ota_error_t last_error;
    uint8_t retry_count;
    
} ota_context_t;

static ota_context_t g_ota_ctx;


/* ============================================================================
 * Forward Declarations
 * ============================================================================
 */
static ota_error_t handle_challenge(const packet_t* pkt);
static ota_error_t handle_manifest(const packet_t* pkt);
static ota_error_t handle_fw_chunk(const packet_t* pkt);
static ota_error_t handle_commit(const packet_t* pkt);
static ota_error_t handle_nack(const packet_t* pkt);
static ota_error_t verify_downloaded_firmware(void);
static ota_error_t commit_update(void);


/* ============================================================================
 * Public Functions
 * ============================================================================
 */

/**
 * @brief Initialize OTA handler
 */
void ota_handler_init(void)
{
    memset(&g_ota_ctx, 0, sizeof(g_ota_ctx));
    g_ota_ctx.state = OTA_STATE_IDLE;
    
    /* Initialize crypto subsystem */
    crypto_init();
}


/**
 * @brief Start OTA session (send HELLO to Gateway)
 */
ota_error_t ota_start_session(void)
{
    if (g_ota_ctx.state != OTA_STATE_IDLE) {
        return OTA_ERR_INVALID_STATE;
    }
    
    /* Generate ephemeral key pair for this session */
    int ret = crypto_generate_x25519_keypair(
        g_ota_ctx.device_private_key,
        g_ota_ctx.device_public_key
    );
    
    if (ret != 0) {
        return OTA_ERR_KEY_DERIVATION;
    }
    
    /* Build HELLO packet */
    hello_payload_t hello;
    hello.device_id = get_device_id();
    hello.device_class[0] = 'F';
    hello.device_class[1] = '1';
    hello.current_fw_version = get_current_fw_version();
    hello.security_version = get_security_counter();
    memcpy(hello.public_key, g_ota_ctx.device_public_key, 32);
    
    /* Send HELLO packet */
    /* TODO: Call UART send function */
    
    g_ota_ctx.state = OTA_STATE_HANDSHAKE;
    return OTA_OK;
}


/**
 * @brief Process received packet
 */
ota_error_t ota_process_packet(const packet_t* pkt)
{
    switch (pkt->header.packet_type) {
        case PKT_TYPE_CHALLENGE:
            return handle_challenge(pkt);
            
        case PKT_TYPE_MANIFEST:
            return handle_manifest(pkt);
            
        case PKT_TYPE_FW_CHUNK:
            return handle_fw_chunk(pkt);
            
        case PKT_TYPE_FW_COMMIT:
            return handle_commit(pkt);
            
        case PKT_TYPE_NACK:
            return handle_nack(pkt);
            
        default:
            return OTA_ERR_NOT_SUPPORTED;
    }
}


/* ============================================================================
 * Packet Handlers
 * ============================================================================
 */

static ota_error_t handle_challenge(const packet_t* pkt)
{
    if (g_ota_ctx.state != OTA_STATE_HANDSHAKE) {
        return OTA_ERR_INVALID_STATE;
    }
    
    /* Parse challenge payload */
    const challenge_payload_t* challenge = (const challenge_payload_t*)pkt->payload;
    
    /* Save server's public key */
    memcpy(g_ota_ctx.server_public_key, challenge->server_public_key, 32);
    
    /* Derive shared secret using X25519 */
    uint8_t shared_secret[32];
    int ret = crypto_x25519_derive(
        shared_secret,
        g_ota_ctx.device_private_key,
        g_ota_ctx.server_public_key
    );
    
    if (ret != 0) {
        g_ota_ctx.last_error = OTA_ERR_KEY_EXCHANGE_FAILED;
        g_ota_ctx.state = OTA_STATE_ERROR;
        return g_ota_ctx.last_error;
    }
    
    /* Derive session key from shared secret */
    crypto_derive_session_key(
        g_ota_ctx.session_key,
        shared_secret,
        challenge->challenge_nonce,
        16
    );
    
    /* Compute ASCON MAC over challenge as authentication */
    uint8_t auth_tag[16];
    crypto_ascon_mac(
        auth_tag,
        g_ota_ctx.session_key,
        challenge->challenge_nonce,
        16
    );
    
    /* Build and send RESPONSE packet */
    response_payload_t response;
    memcpy(response.auth_tag, auth_tag, 16);
    memcpy(response.device_public_key, g_ota_ctx.device_public_key, 32);
    
    /* TODO: Send response packet */
    
    g_ota_ctx.state = OTA_STATE_WAIT_MANIFEST;
    
    /* Clear sensitive data */
    memset(shared_secret, 0, sizeof(shared_secret));
    
    return OTA_OK;
}


static ota_error_t handle_manifest(const packet_t* pkt)
{
    if (g_ota_ctx.state != OTA_STATE_WAIT_MANIFEST) {
        return OTA_ERR_INVALID_STATE;
    }
    
    /* Decrypt manifest if encrypted */
    ota_manifest_t* manifest = &g_ota_ctx.current_manifest;
    
    if (pkt->header.flags & PKT_FLAG_ENCRYPTED) {
        /* Decrypt using session key */
        uint16_t decrypted_len;
        ota_error_t err = crypto_ascon_decrypt(
            (uint8_t*)manifest,
            &decrypted_len,
            g_ota_ctx.session_key,
            g_ota_ctx.nonce_base,
            pkt->payload,
            pkt->header.payload_length,
            NULL,  /* No associated data for manifest */
            0
        );
        
        if (err != OTA_OK) {
            return OTA_ERR_DECRYPT_FAILED;
        }
    } else {
        memcpy(manifest, pkt->payload, sizeof(ota_manifest_t));
    }
    
    /* Verify manifest */
    if (!manifest_is_valid(manifest)) {
        return OTA_ERR_INVALID_MANIFEST;
    }
    
    /* Verify Ed25519 signature */
    ota_error_t err = crypto_verify_manifest_signature(manifest);
    if (err != OTA_OK) {
        return OTA_ERR_INVALID_SIGNATURE;
    }
    
    /* Anti-rollback check */
    if (manifest->security_version < get_security_counter()) {
        return OTA_ERR_VERSION_ROLLBACK;
    }
    
    /* Prepare for download */
    g_ota_ctx.expected_chunks = manifest->total_chunks;
    g_ota_ctx.received_chunks = 0;
    g_ota_ctx.bytes_written = 0;
    g_ota_ctx.target_address = get_inactive_slot_address();
    
    /* Save nonce base for chunk decryption */
    memcpy(g_ota_ctx.nonce_base, manifest->nonce_base, 16);
    
    /* Erase target flash region */
    err = flash_erase_region(g_ota_ctx.target_address, manifest->fw_size);
    if (err != OTA_OK) {
        return err;
    }
    
    /* Send ACK to start download */
    /* TODO: Send ACK packet */
    
    g_ota_ctx.state = OTA_STATE_DOWNLOADING;
    return OTA_OK;
}


static ota_error_t handle_fw_chunk(const packet_t* pkt)
{
    if (g_ota_ctx.state != OTA_STATE_DOWNLOADING) {
        return OTA_ERR_INVALID_STATE;
    }
    
    const fw_chunk_payload_t* chunk = (const fw_chunk_payload_t*)pkt->payload;
    
    /* Validate chunk index */
    if (chunk->chunk_index >= g_ota_ctx.expected_chunks) {
        return OTA_ERR_CHUNK_MISSING;
    }
    
    /* Derive chunk-specific nonce */
    uint8_t chunk_nonce[16];
    memcpy(chunk_nonce, g_ota_ctx.nonce_base, 12);
    memcpy(chunk_nonce + 12, chunk->nonce_counter, 4);
    
    /* Decrypt chunk */
    uint8_t decrypted[1024];
    uint16_t decrypted_len;
    
    ota_error_t err = crypto_ascon_decrypt_chunk(
        decrypted,
        &decrypted_len,
        g_ota_ctx.session_key,
        chunk_nonce,
        chunk->data,
        chunk->chunk_size,
        chunk->chunk_index,
        g_ota_ctx.expected_chunks
    );
    
    if (err != OTA_OK) {
        return OTA_ERR_DECRYPT_FAILED;
    }
    
    /* Write to flash */
    uint32_t write_address = g_ota_ctx.target_address + 
                             (chunk->chunk_index * g_ota_ctx.current_manifest.chunk_size);
    
    err = flash_write(write_address, decrypted, decrypted_len);
    if (err != OTA_OK) {
        return err;
    }
    
    g_ota_ctx.received_chunks++;
    g_ota_ctx.bytes_written += decrypted_len;
    
    /* Check if download complete */
    if (g_ota_ctx.received_chunks >= g_ota_ctx.expected_chunks) {
        g_ota_ctx.state = OTA_STATE_VERIFYING;
        
        /* Verify firmware hash */
        err = verify_downloaded_firmware();
        if (err != OTA_OK) {
            return err;
        }
        
        /* Send verify success */
        /* TODO: Send FW_VERIFY packet with result */
    }
    
    /* Send ACK for this chunk */
    /* TODO: Send ACK */
    
    return OTA_OK;
}


static ota_error_t handle_commit(const packet_t* pkt)
{
    if (g_ota_ctx.state != OTA_STATE_VERIFYING) {
        return OTA_ERR_INVALID_STATE;
    }
    
    (void)pkt;
    
    /* Update boot metadata to use new firmware */
    ota_error_t err = commit_update();
    
    if (err == OTA_OK) {
        /* Send final ACK */
        /* TODO: Send ACK */
        
        /* Reboot to new firmware */
        NVIC_SystemReset();
    }
    
    return err;
}


static ota_error_t handle_nack(const packet_t* pkt)
{
    /* Handle negative acknowledgment */
    (void)pkt;
    
    g_ota_ctx.retry_count++;
    if (g_ota_ctx.retry_count >= 3) {
        g_ota_ctx.state = OTA_STATE_ERROR;
        return OTA_ERR_CONNECTION_LOST;
    }
    
    /* TODO: Retry last operation */
    return OTA_OK;
}


/* ============================================================================
 * Helper Functions
 * ============================================================================
 */

static ota_error_t verify_downloaded_firmware(void)
{
    /* Calculate hash of downloaded firmware */
    uint8_t calculated_hash[32];
    
    crypto_hash_firmware(
        calculated_hash,
        g_ota_ctx.target_address,
        g_ota_ctx.current_manifest.fw_size
    );
    
    /* Compare with manifest hash */
    if (memcmp(calculated_hash, g_ota_ctx.current_manifest.fw_hash, 32) != 0) {
        return OTA_ERR_HASH_MISMATCH;
    }
    
    return OTA_OK;
}


static ota_error_t commit_update(void)
{
    /* Update boot metadata:
     * 1. Mark new slot as pending
     * 2. Update security counter
     * 3. Save metadata to flash
     */
    
    /* TODO: Implement commit logic */
    return OTA_OK;
}


/* External helper function stubs - to be implemented */
uint32_t get_device_id(void) { return 0x12345678; }
uint32_t get_current_fw_version(void) { return 0x01000000; }
uint32_t get_security_counter(void) { return 1; }
uint32_t get_inactive_slot_address(void) { return 0x0800A000; }
