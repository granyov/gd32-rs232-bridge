#include "flow_control.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    bridge_queue_t q = {0};
    assert(flow_queue_used(&q) == 0U);
    q.read = 2040U; q.write = 100U;
    assert(flow_queue_used(&q) == 108U);
    q.read = 0U; q.write = 2047U;
    assert(flow_queue_used(&q) == 2047U);
    assert(flow_rts_next(true, 1535U));
    assert(!flow_rts_next(true, 1536U));
    assert(!flow_rts_next(false, 1535U));
    assert(!flow_rts_next(false, 513U));
    assert(flow_rts_next(false, 512U));
    assert(flow_rts_next(true, 512U));
    assert(flow_cts_allows(false, false));
    assert(flow_cts_allows(false, true));
    assert(!flow_cts_allows(true, false));
    assert(flow_cts_allows(true, true));
    puts("PASS: RTS hysteresis, wrapped queue occupancy, CTS gating");
    return 0;
}
