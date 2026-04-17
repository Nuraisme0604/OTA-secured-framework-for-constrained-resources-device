/**
 * @file protocol_parser.h
 * @brief Protocol Parser for OTA packets
 */

#ifndef PROTOCOL_PARSER_H
#define PROTOCOL_PARSER_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "../../common/protocol_packet.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Parser state */
typedef enum {
    PARSER_STATE_IDLE,
    PARSER_STATE_HEADER,
    PARSER_STATE_PAYLOAD,
    PARSER_STATE_CRC,
    PARSER_STATE_END,
    PARSER_STATE_ERROR,
} parser_state_t;

/* Parser context */
typedef struct {
    parser_state_t state;
    packet_t packet;
    uint16_t bytes_received;
    uint16_t expected_bytes;
} protocol_parser_t;

/**
 * @brief Initialize protocol parser
 */
void protocol_parser_init(protocol_parser_t* parser);

/**
 * @brief Reset parser state
 */
void protocol_parser_reset(protocol_parser_t* parser);

/**
 * @brief Feed a byte to the parser
 * @return 1 if complete packet received, 0 if need more data, -1 on error
 */
int protocol_parser_feed(protocol_parser_t* parser, uint8_t byte);

/**
 * @brief Get parsed packet (only valid after feed returns 1)
 */
const packet_t* protocol_parser_get_packet(protocol_parser_t* parser);

/**
 * @brief Build a packet from components
 */
int protocol_build_packet(packet_t* pkt, packet_type_t type, uint8_t flags,
                          const uint8_t* payload, uint16_t payload_len);

/**
 * @brief Calculate CRC16 for packet
 */
uint16_t protocol_calculate_crc(const packet_t* pkt);

/**
 * @brief Verify packet CRC
 */
bool protocol_verify_crc(const packet_t* pkt);

/**
 * @brief Serialize packet to buffer for transmission
 * @return Number of bytes written, or -1 on error
 */
int protocol_serialize(const packet_t* pkt, uint8_t* buffer, size_t buffer_size);

/**
 * @brief Escape special bytes for transmission
 */
int protocol_escape(const uint8_t* input, size_t input_len, 
                    uint8_t* output, size_t output_size);

#ifdef __cplusplus
}
#endif

#endif /* PROTOCOL_PARSER_H */
