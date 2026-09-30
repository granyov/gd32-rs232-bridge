#ifndef RS232_BRIDGE_H
#define RS232_BRIDGE_H
#include <stdbool.h>
#include <stdint.h>

/* All accesses are from equal-priority, non-preempting USART interrupts.
 * Main must not access the queues. Counters may be inspected via SWD. */
#define BRIDGE_QUEUE_SIZE 2048U
#define BRIDGE_HOST 0U
#define BRIDGE_LOGGER 1U
#define BRIDGE_PARITY  1U
#define BRIDGE_FRAMING 2U
#define BRIDGE_NOISE   4U
#define BRIDGE_OVERRUN 8U

typedef struct {
    uint8_t data[BRIDGE_QUEUE_SIZE];
    uint16_t read, write;
} bridge_queue_t;
typedef struct {
    volatile uint32_t rx_bytes, tx_bytes;
    volatile uint32_t parity, framing, noise, overruns;
    volatile uint32_t corrupt_dropped, queue_dropped;
} bridge_stats_t;
typedef struct {
    bridge_queue_t tx[2];
    bridge_stats_t stats[2];
} bridge_t;

/* Zero-initialize bridge_t before enabling the IRQs. Returns true if a
 * byte was queued for the opposite UART. Overflow drops the NEW byte. */
bool bridge_receive(bridge_t *b, unsigned src, bool has_byte,
                    uint8_t byte, unsigned errors);
bool bridge_next_tx(bridge_t *b, unsigned dst, uint8_t *byte);
#endif
