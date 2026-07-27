#pragma once

/*
 * BOOTMUX R7C-P1 S3 — bounded target-reachability probe (pure core).
 *
 * Host-testable state machine with no ESP-IDF dependency.  The device wiring
 * drives it with real ping_sock results; host tests drive it with synthetic
 * results.  Rules fixed by the NX capsule:
 *
 *   - allowlist is compile-time fixed IPv4 literals only (no DNS, no names)
 *   - only allowlist entries inside the current STA subnet are probe targets
 *   - 3 consecutive successes -> reachable = true
 *   - 2 consecutive failures  -> reachable = false
 *   - 15 s with no probe result -> reachable = false
 *   - probing is forbidden before the STA has an IP (no subnet set)
 *
 * "allowlist_loaded" (the fourth gate input) becomes true only once a valid STA
 * subnet has been supplied that matches at least one allowlist entry.  An
 * unknown router subnet therefore can never open the management path.
 */

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TP_REACHABLE_SUCCESSES 3
#define TP_UNREACHABLE_FAILURES 2
#define TP_NO_RESPONSE_MS 15000

/* Build an IPv4 literal as a host-order 32-bit integer.  Endianness is
 * irrelevant as long as every value in this module uses the same convention. */
static inline uint32_t tp_ipv4(uint8_t a, uint8_t b, uint8_t c, uint8_t d) {
    return ((uint32_t)a << 24) | ((uint32_t)b << 16) | ((uint32_t)c << 8) | (uint32_t)d;
}

typedef struct {
    bool initialized;        /* tp_init called */
    bool subnet_set;         /* a valid STA subnet has been supplied */
    bool allowlist_loaded;   /* subnet matches >=1 allowlist entry */
    bool reachable;
    int consecutive_success;
    int consecutive_failure;
    int64_t last_result_ms;  /* timestamp of the most recent probe result */
    uint32_t sta_ip;
    uint32_t sta_netmask;
    uint32_t selected_target; /* in-subnet allowlist entry to probe, 0 if none */
} tp_state_t;

/* Reset to the boot state: not initialized, not reachable, no subnet. */
void tp_init(tp_state_t *state);

/*
 * Supply the current STA IPv4 address and netmask (host order).  Selects the
 * first allowlist entry that shares the STA subnet.  Sets allowlist_loaded when
 * a match exists.  A zero address or zero netmask clears the subnet (used on
 * Wi-Fi disconnect) and drops allowlist_loaded and reachability.
 */
void tp_set_subnet(tp_state_t *state, uint32_t sta_ip, uint32_t sta_netmask);

/* True when the fixed allowlist is present and matched to the current subnet. */
bool tp_allowlist_loaded(const tp_state_t *state);

/* True when probing is permitted (initialized and a subnet is set). */
bool tp_probe_allowed(const tp_state_t *state);

/* Return the allowlist target to probe next, or 0 if probing is not allowed or
 * no in-subnet target exists. */
uint32_t tp_select_target(const tp_state_t *state);

/*
 * Record one bounded probe result.  Ignored unless probing is allowed.  Updates
 * the consecutive counters and the reachability latch per the fixed rules.
 */
void tp_record_result(tp_state_t *state, bool success, int64_t now_ms);

/*
 * Current reachability, applying the 15 s no-response decay against now_ms.
 * Reading this may transition reachable -> false when the window has elapsed.
 */
bool tp_is_reachable(tp_state_t *state, int64_t now_ms);

#ifdef __cplusplus
}
#endif
