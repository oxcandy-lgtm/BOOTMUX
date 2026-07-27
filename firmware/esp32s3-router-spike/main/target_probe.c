#include "target_probe.h"

#include <stddef.h>

/* Compile-time IPv4 literal helper usable in static initializers. */
#define TP_IPV4(a, b, c, d) \
    (((uint32_t)(a) << 24) | ((uint32_t)(b) << 16) | ((uint32_t)(c) << 8) | (uint32_t)(d))

/*
 * V1 management allowlist — compile-time fixed IPv4 literals only.  No DNS, no
 * names, no runtime configuration.  These are the only addresses the probe may
 * ever target, and only the one sharing the current STA subnet is used.
 */
static const uint32_t kAllowlist[] = {
    TP_IPV4(192, 168, 11, 1),
    TP_IPV4(192, 168, 77, 1),
};
#define TP_ALLOWLIST_COUNT (sizeof(kAllowlist) / sizeof(kAllowlist[0]))

void tp_init(tp_state_t *state) {
    if (!state) return;
    state->initialized = true;
    state->subnet_set = false;
    state->allowlist_loaded = false;
    state->reachable = false;
    state->consecutive_success = 0;
    state->consecutive_failure = 0;
    state->last_result_ms = 0;
    state->sta_ip = 0;
    state->sta_netmask = 0;
    state->selected_target = 0;
}

static bool same_subnet(uint32_t a, uint32_t b, uint32_t mask) {
    return (a & mask) == (b & mask);
}

void tp_set_subnet(tp_state_t *state, uint32_t sta_ip, uint32_t sta_netmask) {
    if (!state) return;
    if (!state->initialized) tp_init(state);
    if (sta_ip == 0 || sta_netmask == 0) {
        state->subnet_set = false;
        state->allowlist_loaded = false;
        state->reachable = false;
        state->consecutive_success = 0;
        state->consecutive_failure = 0;
        state->sta_ip = 0;
        state->sta_netmask = 0;
        state->selected_target = 0;
        return;
    }
    state->subnet_set = true;
    state->sta_ip = sta_ip;
    state->sta_netmask = sta_netmask;
    state->selected_target = 0;
    state->allowlist_loaded = false;
    for (size_t i = 0; i < TP_ALLOWLIST_COUNT; ++i) {
        if (same_subnet(kAllowlist[i], sta_ip, sta_netmask)) {
            state->selected_target = kAllowlist[i];
            state->allowlist_loaded = true;
            break;
        }
    }
    /* A subnet change invalidates any prior reachability evidence. */
    state->reachable = false;
    state->consecutive_success = 0;
    state->consecutive_failure = 0;
    state->last_result_ms = 0;
}

bool tp_allowlist_loaded(const tp_state_t *state) {
    return state && state->initialized && state->allowlist_loaded;
}

bool tp_probe_allowed(const tp_state_t *state) {
    return state && state->initialized && state->subnet_set && state->selected_target != 0;
}

uint32_t tp_select_target(const tp_state_t *state) {
    if (!tp_probe_allowed(state)) return 0;
    return state->selected_target;
}

void tp_record_result(tp_state_t *state, bool success, int64_t now_ms) {
    if (!state || !tp_probe_allowed(state)) return;
    state->last_result_ms = now_ms;
    if (success) {
        state->consecutive_failure = 0;
        if (state->consecutive_success < TP_REACHABLE_SUCCESSES) ++state->consecutive_success;
        if (state->consecutive_success >= TP_REACHABLE_SUCCESSES) state->reachable = true;
    } else {
        state->consecutive_success = 0;
        if (state->consecutive_failure < TP_UNREACHABLE_FAILURES) ++state->consecutive_failure;
        if (state->consecutive_failure >= TP_UNREACHABLE_FAILURES) state->reachable = false;
    }
}

bool tp_is_reachable(tp_state_t *state, int64_t now_ms) {
    if (!state || !state->initialized) return false;
    if (!state->reachable) return false;
    if (state->last_result_ms != 0 && now_ms - state->last_result_ms >= TP_NO_RESPONSE_MS) {
        state->reachable = false;
        state->consecutive_success = 0;
    }
    return state->reachable;
}
