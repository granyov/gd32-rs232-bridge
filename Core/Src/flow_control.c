#include "flow_control.h"

_Static_assert(FLOW_RTS_RESUME_AT < FLOW_RTS_PAUSE_AT,
               "RTS hysteresis thresholds must not overlap");
_Static_assert(FLOW_RTS_PAUSE_AT < BRIDGE_QUEUE_SIZE - 1U,
               "RTS pause point must be below queue capacity");

uint16_t flow_queue_used(const bridge_queue_t *queue) {
    return (uint16_t)((queue->write - queue->read) & (BRIDGE_QUEUE_SIZE - 1U));
}
bool flow_rts_next(bool currently_asserted, uint16_t used) {
    if (currently_asserted && used >= FLOW_RTS_PAUSE_AT) return false;
    if (!currently_asserted && used <= FLOW_RTS_RESUME_AT) return true;
    return currently_asserted;
}
bool flow_cts_allows(bool enabled, bool external_cts_asserted) {
    return !enabled || external_cts_asserted;
}
