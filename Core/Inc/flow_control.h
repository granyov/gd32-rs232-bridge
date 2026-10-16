#ifndef LAZARUS_FLOW_CONTROL_H
#define LAZARUS_FLOW_CONTROL_H
#include "bridge.h"
#include <stdbool.h>
#include <stdint.h>

#define FLOW_RTS_PAUSE_AT 1536U
#define FLOW_RTS_RESUME_AT 512U

/* Pure decision functions, no GPIO dependency, suitable for unit tests. */
uint16_t flow_queue_used(const bridge_queue_t *queue);
bool flow_rts_next(bool currently_asserted, uint16_t used);
bool flow_cts_allows(bool enabled, bool external_cts_asserted);
#endif
