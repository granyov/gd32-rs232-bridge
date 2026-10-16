#include "config.h"
#include <stddef.h>

#ifndef HOST_BAUD
#define HOST_BAUD 38400U
#endif
#ifndef LOGGER_BAUD
#define LOGGER_BAUD 38400U
#endif

_Static_assert(sizeof(config_record_t) == 32U, "Configuration wire size changed");
_Static_assert(offsetof(config_record_t, crc32) == 28U, "Configuration CRC offset changed");

volatile uint32_t active_config_slot;

uint32_t config_crc32(const config_record_t *config) {
    const uint8_t *data = (const uint8_t *)config;
    uint32_t crc = 0xFFFFFFFFU;
    for (unsigned i = 0; i < offsetof(config_record_t, crc32); ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8U; ++bit) {
            crc = (crc >> 1U) ^ ((crc & 1U) ? 0xEDB88320U : 0U);
        }
    }
    return crc ^ 0xFFFFFFFFU;
}

static bool valid_frame(uint8_t bits, uint8_t parity, uint8_t stop) {
    if (stop != 1U && stop != 2U) return false;
    if (parity > CONFIG_PARITY_ODD) return false;
    /* GD32F103 USART supports 7 data bits only when parity occupies bit 8. */
    return bits == 8U || (bits == 7U && parity != CONFIG_PARITY_NONE);
}

bool config_valid(const config_record_t *config) {
    if (config == NULL ||
        config->magic != CONFIG_MAGIC ||
        config->layout != CONFIG_LAYOUT ||
        config->sequence == 0U ||
        config->sequence == 0xFFFFFFFFU ||
        config->reserved != 0U ||
        config->flow > CONFIG_FLOW_RTS_CTS) return false;
    if (config->host_baud < 1200U || config->host_baud > 115200U ||
        config->rs232_baud < 1200U || config->rs232_baud > 115200U) return false;
    if (!valid_frame(config->host_bits, config->host_parity, config->host_stop) ||
        !valid_frame(config->rs232_bits, config->rs232_parity, config->rs232_stop))
        return false;
    return config->crc32 == config_crc32(config);
}

const config_record_t *config_select(const config_record_t *a,
                                    const config_record_t *b) {
    bool av = config_valid(a), bv = config_valid(b);
    if (!av) return bv ? b : NULL;
    if (!bv) return a;
    /* RFC1982-style serial ordering; the tool advances by one. */
    return (int32_t)(b->sequence - a->sequence) > 0 ? b : a;
}

void config_load(config_record_t *config) {
    const config_record_t *a = (const config_record_t *)CONFIG_SLOT_A_ADDR;
    const config_record_t *b = (const config_record_t *)CONFIG_SLOT_B_ADDR;
    const config_record_t *active = config_select(a, b);
    if (active != NULL) {
        *config = *active;
        active_config_slot = (active == a) ? 1U : 2U;
        return;
    }
    /* A damaged or blank configuration cannot make UART settings undefined. */
    *config = (config_record_t){
        .magic = CONFIG_MAGIC, .layout = CONFIG_LAYOUT, .sequence = 0,
        .host_baud = HOST_BAUD, .rs232_baud = LOGGER_BAUD,
        .host_bits = 8, .host_parity = CONFIG_PARITY_NONE, .host_stop = 1,
        .rs232_bits = 8, .rs232_parity = CONFIG_PARITY_NONE, .rs232_stop = 1,
        .flow = CONFIG_FLOW_NONE
    };
    active_config_slot = 0U;
}
