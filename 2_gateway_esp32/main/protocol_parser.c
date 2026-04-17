/**
 * @file protocol_parser.c
 * @brief Implementation of Protocol Parser and Packet Utilities
 */

#include "protocol_parser.h"
#include <string.h>

/* CRC16-CCITT Lookup Table (Polynomial 0x1021) */
static const uint16_t crc16_table[256] = {
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3ab2,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0
};

uint16_t crc16_ccitt(const uint8_t* data, uint16_t length) {
    uint16_t crc = 0xFFFF;
    while (length--) {
        crc = (crc << 8) ^ crc16_table[((crc >> 8) ^ *data++) & 0xFF];
    }
    return crc;
}

/* ========================================================================
 * Protocol Packet Functions
 * ======================================================================== */

int packet_build(packet_t* pkt, packet_type_t type, uint8_t flags, 
                 uint8_t seq, const uint8_t* payload, uint16_t payload_len) {
    if (!pkt || payload_len > MAX_PAYLOAD_SIZE) return -1;
    
    pkt->header.start_byte = FRAME_START_BYTE;
    pkt->header.packet_type = type;
    pkt->header.flags = flags;
    pkt->header.sequence_num = seq;
    pkt->header.payload_length = payload_len;
    
    if (payload && payload_len > 0) {
        memcpy(pkt->payload, payload, payload_len);
    }
    
    /* CRC over Header + Payload */
    pkt->crc16 = crc16_ccitt((uint8_t*)&pkt->header, sizeof(packet_header_t));
    if (payload_len > 0) {
        uint16_t payload_crc = crc16_ccitt(pkt->payload, payload_len);
        /* CRC chaining logic depends on implementation, usually we do continous CRC */
        /* Assuming simple continous CRC manually or recalculating for whole buffer */
        /* Re-calc whole buffer for simplicity */
        uint16_t crc = 0xFFFF;
        const uint8_t* p = (const uint8_t*)&pkt->header;
        for(size_t i=0; i<sizeof(packet_header_t); i++) 
            crc = (crc << 8) ^ crc16_table[((crc >> 8) ^ p[i]) & 0xFF];
        p = pkt->payload;
        for(size_t i=0; i<payload_len; i++)
             crc = (crc << 8) ^ crc16_table[((crc >> 8) ^ p[i]) & 0xFF];
        pkt->crc16 = crc;
    }
    
    pkt->end_byte = FRAME_END_BYTE;
    return 0;
}

uint16_t protocol_calculate_crc(const packet_t* pkt) {
     uint16_t crc = 0xFFFF;
     const uint8_t* p = (const uint8_t*)&pkt->header;
     for(size_t i=0; i<sizeof(packet_header_t); i++) 
         crc = (crc << 8) ^ crc16_table[((crc >> 8) ^ p[i]) & 0xFF];
     
     if (pkt->header.payload_length > 0) {
         p = pkt->payload;
         for(size_t i=0; i<pkt->header.payload_length; i++)
              crc = (crc << 8) ^ crc16_table[((crc >> 8) ^ p[i]) & 0xFF];
     }
     return crc;
}

/* ========================================================================
 * Protocol Parser Functions
 * ======================================================================== */

void protocol_parser_init(protocol_parser_t* parser) {
    if (parser) {
        memset(parser, 0, sizeof(protocol_parser_t));
        parser->state = PARSER_STATE_IDLE;
    }
}

void protocol_parser_reset(protocol_parser_t* parser) {
    if (parser) {
        parser->state = PARSER_STATE_IDLE;
        parser->bytes_received = 0;
        parser->expected_bytes = 0;
    }
}

int protocol_parser_feed(protocol_parser_t* parser, uint8_t byte) {
    if (!parser) return -1;
    
    switch (parser->state) {
        case PARSER_STATE_IDLE:
            if (byte == FRAME_START_BYTE) {
                parser->state = PARSER_STATE_HEADER;
                parser->bytes_received = 0;
                /* Store start byte */
                ((uint8_t*)&parser->packet.header)[0] = byte;
                parser->bytes_received++;
            }
            break;
            
        case PARSER_STATE_HEADER:
            ((uint8_t*)&parser->packet.header)[parser->bytes_received++] = byte;
            
            if (parser->bytes_received >= sizeof(packet_header_t)) {
                /* Header complete, check payload length */
                uint16_t payload_len = parser->packet.header.payload_length;
                if (payload_len > MAX_PAYLOAD_SIZE) {
                    parser->state = PARSER_STATE_ERROR;
                    return -1;
                }
                
                if (payload_len > 0) {
                    parser->state = PARSER_STATE_PAYLOAD;
                    parser->expected_bytes = payload_len;
                    parser->bytes_received = 0;
                } else {
                    parser->state = PARSER_STATE_CRC;
                    parser->bytes_received = 0;
                }
            }
            break;
            
        case PARSER_STATE_PAYLOAD:
            parser->packet.payload[parser->bytes_received++] = byte;
            if (parser->bytes_received >= parser->expected_bytes) {
                parser->state = PARSER_STATE_CRC;
                parser->bytes_received = 0;
            }
            break;
            
        case PARSER_STATE_CRC:
             if (parser->bytes_received == 0) {
                 parser->packet.crc16 = byte; /* Low byte or High? usually Big Endian or Little? Assuming Little Endian for struct? */
                 /* Actually typically structs are LE on ARM/Xtensa. Let's assume byte order matches */
                 /* We should probably handle endianness properly. */
                 /* For now assume matching endianness */
             } else {
                 parser->packet.crc16 |= (uint16_t)byte << 8; /* If first was low, this is high? */
                 /* Depends on sender. Let's assume simple byte stream filling struct */
                 /* Wait, feed order matters. If sender sends struct directly, it depends on their endianness. */
                 /* Let's buffer it properly later if issues arise. */
             }
             
             /* Buffer CRC into struct using pointer math to be safe about stream order matching struct layout */
             /* Actually simpler: just fill the struct bytes linearly? No, packet layout has payload in middle. */
             
             /* Re-implement CRC state properly: */
             /* We need 2 bytes for CRC */
             if (parser->bytes_received == 0) {
                 /* First byte of CRC */
                 /* If network order (Big Endian)? Protocol usually specifies. */
                 /* Assuming Little Endian (lower byte first) as per typical struct packing on these MCUs */
                 ((uint8_t*)&parser->packet.crc16)[0] = byte;
                 parser->bytes_received++;
             } else {
                 ((uint8_t*)&parser->packet.crc16)[1] = byte;
                 parser->state = PARSER_STATE_END;
             }
             break;
             
        case PARSER_STATE_END:
            if (byte == FRAME_END_BYTE) {
                parser->packet.end_byte = byte;
                /* Verify CRC */
                uint16_t calc_crc = protocol_calculate_crc(&parser->packet);
                if (calc_crc == parser->packet.crc16) {
                    parser->state = PARSER_STATE_IDLE;
                    return 1; /* Complete packet */
                } else {
                    parser->state = PARSER_STATE_ERROR; /* CRC Mismatch */
                    return -2;
                }
            } else {
                parser->state = PARSER_STATE_ERROR;
                return -1;
            }
            break;
            
        case PARSER_STATE_ERROR:
            if (byte == FRAME_START_BYTE) {
                 protocol_parser_reset(parser);
                 protocol_parser_feed(parser, byte);
            }
            break;
    }
    
    return 0;
}

int protocol_serialize(const packet_t* pkt, uint8_t* buffer, size_t buffer_size) {
    if (!pkt || !buffer) return -1;
    
    size_t total_len = sizeof(packet_header_t) + pkt->header.payload_length + 3; /* CRC(2) + End(1) */
    if (buffer_size < total_len) return -1;
    
    uint8_t* ptr = buffer;
    
    /* Header */
    memcpy(ptr, &pkt->header, sizeof(packet_header_t));
    ptr += sizeof(packet_header_t);
    
    /* Payload */
    if (pkt->header.payload_length > 0) {
        memcpy(ptr, pkt->payload, pkt->header.payload_length);
        ptr += pkt->header.payload_length;
    }
    
    /* CRC */
    memcpy(ptr, &pkt->crc16, 2);
    ptr += 2;
    
    /* End Byte */
    *ptr = pkt->end_byte;
    
    return (int)total_len;
}
