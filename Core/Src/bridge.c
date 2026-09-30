#include "bridge.h"

_Static_assert((BRIDGE_QUEUE_SIZE & (BRIDGE_QUEUE_SIZE - 1U)) == 0,
               "Queue size must be a power of two");
_Static_assert(BRIDGE_QUEUE_SIZE <= 32768U, "Queue index must fit uint16_t");

bool bridge_receive(bridge_t *b, unsigned src, bool has_byte,
                    uint8_t byte, unsigned errors) {
    bridge_stats_t *s = &b->stats[src];
    if (errors & BRIDGE_PARITY) ++s->parity;
    if (errors & BRIDGE_FRAMING) ++s->framing;
    if (errors & BRIDGE_NOISE) ++s->noise;
    if (errors & BRIDGE_OVERRUN) ++s->overruns;
    if (!has_byte) return false;
    ++s->rx_bytes;
    if (errors & (BRIDGE_PARITY | BRIDGE_FRAMING | BRIDGE_NOISE)) {
        ++s->corrupt_dropped;
        return false;
    }
    /* On ORE the byte already in DR remains valid; a later byte was lost. */
    bridge_queue_t *q = &b->tx[src ^ 1U];
    uint16_t next = (uint16_t)((q->write + 1U) & (BRIDGE_QUEUE_SIZE - 1U));
    if (next == q->read) {
        ++s->queue_dropped;
        return false;
    }
    q->data[q->write] = byte;
    q->write = next;
    return true;
}

bool bridge_next_tx(bridge_t *b, unsigned dst, uint8_t *byte) {
    bridge_queue_t *q = &b->tx[dst];
    if (q->read == q->write) return false;
    *byte = q->data[q->read];
    q->read = (uint16_t)((q->read + 1U) & (BRIDGE_QUEUE_SIZE - 1U));
    ++b->stats[dst].tx_bytes;
    return true;
}
