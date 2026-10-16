#include "config.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static config_record_t standard(uint32_t sequence) {
    config_record_t c = {
        .magic = CONFIG_MAGIC, .layout = CONFIG_LAYOUT,
        .sequence = sequence, .host_baud = 38400, .rs232_baud = 19200,
        .host_bits = 8, .host_parity = CONFIG_PARITY_NONE, .host_stop = 1,
        .rs232_bits = 7, .rs232_parity = CONFIG_PARITY_EVEN, .rs232_stop = 2,
        .flow = CONFIG_FLOW_RTS_CTS
    };
    c.crc32 = config_crc32(&c);
    return c;
}
int main(void) {
    config_record_t a = standard(1), b = standard(2);
    /* Cross-language golden bytes: Python '<IIIII8BI' / zlib CRC32.
     * A mismatch would make SWD-written pages unreadable by firmware. */
    const uint8_t golden[32] = {0x4c, 0x52, 0x57, 0x31, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x96, 0x00, 0x00, 0x00, 0x4b, 0x00, 0x00, 0x08, 0x00, 0x01, 0x07, 0x01, 0x02, 0x01, 0x00, 0xb0, 0x49, 0xcf, 0x0d};
    assert(memcmp(&a, golden, sizeof(golden)) == 0);
    assert(config_crc32(&a) == 0x0dcf49b0U);
    assert(config_valid(&a) && config_valid(&b));
    assert(config_select(&a, &b) == &b);
    b.crc32 ^= 1U;
    assert(!config_valid(&b));
    assert(config_select(&a, &b) == &a);
    a.magic = 0xFFFFFFFFU;
    assert(config_select(&a, &b) == NULL);
    a = standard(0xFFFFFFFEU); b = standard(1U);
    assert(config_select(&a, &b) == &b);
    b = standard(2U); b.host_bits = 7U; b.host_parity = CONFIG_PARITY_NONE;
    b.crc32 = config_crc32(&b);
    assert(!config_valid(&b));
    b = standard(2U); b.rs232_baud = 230400U; b.crc32 = config_crc32(&b);
    assert(!config_valid(&b));
    b = standard(2U); b.reserved = 1U; b.crc32 = config_crc32(&b);
    assert(!config_valid(&b));
    puts("PASS: CRC32, validation, slot failover, sequence rollover");
    return 0;
}
