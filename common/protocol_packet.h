/**
 * @file protocol_packet.h
 * @brief Định dạng gói tin UART cho giao tiếp Gateway-Node
 * 
 * Giao thức truyền thông giữa ESP32 Gateway và STM32 Node qua UART.
 * Sử dụng frame-based protocol với Start/End markers và CRC16.
 */

#ifndef PROTOCOL_PACKET_H
#define PROTOCOL_PACKET_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Frame markers */
#define FRAME_START_BYTE    0x7E
#define FRAME_END_BYTE      0x7F
#define FRAME_ESCAPE_BYTE   0x7D
#define FRAME_XOR_VALUE     0x20

/* Kích thước tối đa */
#define MAX_PAYLOAD_SIZE    1024    /* 1KB chunk */
#define MAX_FRAME_SIZE      (MAX_PAYLOAD_SIZE + 16)  /* Payload + overhead */

/* Packet Types - OTA Protocol */
typedef enum {
    /* Handshake & Session */
    PKT_TYPE_HELLO          = 0x01,  /* Node -> Gateway: Khởi tạo session */
    PKT_TYPE_CHALLENGE      = 0x02,  /* Gateway -> Node: Challenge cho CRA */
    PKT_TYPE_RESPONSE       = 0x03,  /* Node -> Gateway: Response (ASCON MAC) */
    PKT_TYPE_SESSION_KEY    = 0x04,  /* Gateway -> Node: Encrypted session key */
    PKT_TYPE_ACK            = 0x05,  /* Bidirectional: Acknowledgment */
    PKT_TYPE_NACK           = 0x06,  /* Bidirectional: Negative acknowledgment */
    
    /* OTA Transfer */
    PKT_TYPE_MANIFEST       = 0x10,  /* Gateway -> Node: OTA Manifest */
    PKT_TYPE_FW_CHUNK       = 0x11,  /* Gateway -> Node: Firmware chunk */
    PKT_TYPE_FW_VERIFY      = 0x12,  /* Node -> Gateway: Verification result */
    PKT_TYPE_FW_COMMIT      = 0x13,  /* Gateway -> Node: Commit update */
    PKT_TYPE_FW_ROLLBACK    = 0x14,  /* Gateway -> Node: Rollback command */
    
    /* Status & Control */
    PKT_TYPE_STATUS_REQ     = 0x20,  /* Gateway -> Node: Request status */
    PKT_TYPE_STATUS_RSP     = 0x21,  /* Node -> Gateway: Status response */
    PKT_TYPE_REBOOT         = 0x22,  /* Gateway -> Node: Reboot command */
    PKT_TYPE_RESET_SESSION  = 0x23,  /* Bidirectional: Reset session */
    
    /* Error */
    PKT_TYPE_ERROR          = 0xFF,  /* Error packet */
} packet_type_t;

/* Packet Flags */
#define PKT_FLAG_ENCRYPTED  0x01    /* Payload is ASCON encrypted */
#define PKT_FLAG_COMPRESSED 0x02    /* Payload is compressed */
#define PKT_FLAG_FRAGMENTED 0x04    /* Packet is fragmented */
#define PKT_FLAG_LAST_FRAG  0x08    /* Last fragment */
#define PKT_FLAG_REQUIRE_ACK 0x10   /* Require acknowledgment */

#pragma pack(push, 1)

/**
 * @brief Header của gói tin
 * 
 * Layout: [START][HEADER][PAYLOAD][CRC16][END]
 */
typedef struct {
    uint8_t  start_byte;            /* FRAME_START_BYTE (0x7E) */
    uint8_t  packet_type;           /* Loại gói tin (packet_type_t) */
    uint8_t  flags;                 /* Packet flags */
    uint8_t  sequence_num;          /* Sequence number (0-255, wrap around) */
    uint16_t payload_length;        /* Độ dài payload (0 - MAX_PAYLOAD_SIZE) */
} packet_header_t;

/**
 * @brief Cấu trúc gói tin hoàn chỉnh
 */
typedef struct {
    packet_header_t header;
    uint8_t  payload[MAX_PAYLOAD_SIZE];
    uint16_t crc16;                 /* CRC16-CCITT của header + payload */
    uint8_t  end_byte;              /* FRAME_END_BYTE (0x7F) */
} packet_t;

/**
 * @brief Payload cho PKT_TYPE_HELLO
 */
typedef struct {
    uint32_t device_id;             /* Device unique ID */
    uint8_t  device_class[2];       /* Device class */
    uint32_t current_fw_version;    /* Current firmware version */
    uint32_t security_version;      /* Current security counter */
    uint8_t  public_key[32];        /* Device ephemeral public key (X25519) */
} hello_payload_t;

/**
 * @brief Payload cho PKT_TYPE_CHALLENGE
 */
typedef struct {
    uint8_t  challenge_nonce[16];   /* Random challenge */
    uint8_t  server_public_key[32]; /* Server ephemeral public key */
} challenge_payload_t;

/**
 * @brief Payload cho PKT_TYPE_RESPONSE
 */
typedef struct {
    uint8_t  auth_tag[16];          /* ASCON-128a MAC over challenge */
    uint8_t  device_public_key[32]; /* Device ephemeral public key */
} response_payload_t;

/**
 * @brief Payload cho PKT_TYPE_FW_CHUNK
 */
typedef struct {
    uint16_t chunk_index;           /* Index của chunk (0-based) */
    uint16_t chunk_size;            /* Kích thước chunk thực tế */
    uint8_t  nonce_counter[4];      /* Counter cho nonce derivation */
    uint8_t  data[];                /* Encrypted chunk data (flexible array) */
} fw_chunk_payload_t;

#pragma pack(pop)

/* CRC16-CCITT calculation */
uint16_t crc16_ccitt(const uint8_t* data, uint16_t length);

/* Packet building/parsing functions */
int packet_build(packet_t* pkt, packet_type_t type, uint8_t flags, 
                 uint8_t seq, const uint8_t* payload, uint16_t payload_len);
int packet_parse(const uint8_t* buffer, uint16_t buf_len, packet_t* pkt);
int packet_validate_crc(const packet_t* pkt);

#ifdef __cplusplus
}
#endif

#endif /* PROTOCOL_PACKET_H */
