#ifndef LAZARUS_RS232_CONFIG_H
#define LAZARUS_RS232_CONFIG_H

#include <stdbool.h>
#include <stdint.h>

/* GD32F103C8T6, 64 KiB Flash; GD32F10x MD page size 1 KiB. */
#define CONFIG_SLOT_A_ADDR 0x0800F800UL
#define CONFIG_SLOT_B_ADDR 0x0800FC00UL
#define CONFIG_PAGE_SIZE 1024U
#define CONFIG_MAGIC 0x3157524CUL /* ASCII bytes "LRW1", little-endian */
#define CONFIG_LAYOUT 1U
#define CONFIG_PARITY_NONE 0U
#define CONFIG_PARITY_EVEN 1U
#define CONFIG_PARITY_ODD 2U
#define CONFIG_FLOW_NONE 0U
#define CONFIG_FLOW_RTS_CTS 1U

/* Exactly 32 bytes, little-endian, CRC32/ISO-HDLC over the first 28 bytes.
 * Flash is provisioned by a debug probe, never written by this firmware. */
typedef struct {
    uint32_t magic;
    uint32_t layout;
    uint32_t sequence;
    uint32_t host_baud;
    uint32_t rs232_baud;
    uint8_t host_bits;
    uint8_t host_parity;
    uint8_t host_stop;
    uint8_t rs232_bits;
    uint8_t rs232_parity;
    uint8_t rs232_stop;
    uint8_t flow;
    uint8_t reserved;
    uint32_t crc32;
} config_record_t;

extern volatile uint32_t active_config_slot; /* SWD: 0=factory, 1=A, 2=B */

uint32_t config_crc32(const config_record_t *config);
bool config_valid(const config_record_t *config);
const config_record_t *config_select(const config_record_t *a,
                                    const config_record_t *b);
void config_load(config_record_t *config);
#endif
