#include "bridge.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static bridge_t b;
static void reset(void) { memset(&b, 0, sizeof b); }
static void transfer(void) {
    reset();
    uint8_t byte;
    assert(!bridge_next_tx(&b, BRIDGE_HOST, &byte));
    assert(!bridge_next_tx(&b, BRIDGE_LOGGER, &byte));
    /* Both directions, all byte values, many queue wraps and odd chunks. */
    for (unsigned round = 0; round < 1000; ++round) {
        for (unsigned i = 0; i < 117; ++i) {
            assert(bridge_receive(&b, BRIDGE_HOST, true, (uint8_t)(i+round), 0));
            assert(bridge_receive(&b, BRIDGE_LOGGER, true, (uint8_t)(255-i-round), 0));
        }
        for (unsigned i = 0; i < 117; ++i) {
            assert(bridge_next_tx(&b, BRIDGE_LOGGER, &byte));
            assert(byte == (uint8_t)(i+round));
            assert(bridge_next_tx(&b, BRIDGE_HOST, &byte));
            assert(byte == (uint8_t)(255-i-round));
        }
        assert(!bridge_next_tx(&b, BRIDGE_LOGGER, &byte));
        assert(!bridge_next_tx(&b, BRIDGE_HOST, &byte));
    }
    assert(b.stats[0].rx_bytes == 117000 && b.stats[1].tx_bytes == 117000);
    assert(b.stats[1].rx_bytes == 117000 && b.stats[0].tx_bytes == 117000);
    puts("PASS: bidirectional 234000-byte transfer, wraparound, no injected bytes");
}
static void overflow(void) {
    reset();
    for (unsigned i = 0; i < BRIDGE_QUEUE_SIZE - 1; ++i)
        assert(bridge_receive(&b, 0, true, (uint8_t)i, 0));
    assert(!bridge_receive(&b, 0, true, 0xAA, 0));
    assert(b.stats[0].queue_dropped == 1);
    uint8_t byte;
    for (unsigned i = 0; i < BRIDGE_QUEUE_SIZE - 1; ++i) {
        assert(bridge_next_tx(&b, 1, &byte));
        assert(byte == (uint8_t)i);
    }
    assert(!bridge_next_tx(&b, 1, &byte));
    assert(bridge_receive(&b, 0, true, 0x55, 0));
    assert(bridge_next_tx(&b, 1, &byte) && byte == 0x55);
    puts("PASS: full queue drops newest byte, preserves order and resumes");
}
static void errors(void) {
    reset();
    uint8_t byte;
    assert(!bridge_receive(&b, 0, true, 1, BRIDGE_PARITY));
    assert(!bridge_receive(&b, 0, true, 2, BRIDGE_FRAMING));
    assert(!bridge_receive(&b, 0, true, 3, BRIDGE_NOISE));
    assert(!bridge_receive(&b, 0, false, 0, BRIDGE_OVERRUN));
    assert(!bridge_next_tx(&b, 1, &byte));
    assert(bridge_receive(&b, 0, true, 0x42, BRIDGE_OVERRUN));
    assert(bridge_next_tx(&b, 1, &byte) && byte == 0x42);
    assert(bridge_receive(&b, 0, true, 0x43, 0));
    assert(bridge_next_tx(&b, 1, &byte) && byte == 0x43);
    assert(b.stats[0].parity == 1 && b.stats[0].framing == 1);
    assert(b.stats[0].noise == 1 && b.stats[0].overruns == 2);
    assert(b.stats[0].corrupt_dropped == 3);
    puts("PASS: corrupt-byte filtering, overrun accounting and subsequent traffic");
}
int main(void) { transfer(); overflow(); errors(); return 0; }
