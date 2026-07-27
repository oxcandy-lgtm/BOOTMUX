#pragma once

/*
 * BOOTMUX R7C-P1 S3 — single management-path gate controller (pure core).
 *
 * This module is deliberately free of ESP-IDF dependencies so the gate truth
 * table (T1..T16) can be exercised by a plain host unit test.  It owns:
 *
 *   - the four-condition "should open" predicate
 *   - the bounded 60s management lease (absolute deadline, no auto-grant)
 *   - the single reconcile() that drives activation/withdrawal in fixed order
 *   - the fixed, secret-free fail-closed reason codes
 *
 * Side effects (USB netif / NAPT / proxy) are injected through mg_actions_t so
 * the device wiring supplies the real implementations while host tests supply
 * recording stubs.  The gate never touches credentials, SSIDs, or IP literals.
 */

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Result code for injected actions.  Kept independent of esp_err_t so this
 * header compiles on a bare host toolchain.  Device glue maps ESP_OK -> MG_OK. */
typedef int mg_err_t;
#define MG_OK 0
#define MG_FAIL (-1)

/* Bounded management-lease TTL, in seconds.  The NX capsule fixes 10..60. */
#define MG_LEASE_TTL_MIN 10
#define MG_LEASE_TTL_MAX 60

/* Fixed, secret-free fail-closed reason codes.  mg_reason_str() maps these to
 * the exact tokens required by the NX capsule. */
typedef enum {
    MG_REASON_BOOT,
    MG_REASON_WIFI_NO_IP,
    MG_REASON_WIFI_DISCONNECTED,
    MG_REASON_TARGET_UNREACHABLE,
    MG_REASON_LEASE_ABSENT,
    MG_REASON_LEASE_EXPIRED,
    MG_REASON_BLE_DISCONNECTED,
    MG_REASON_WIFI_CLEARED,
    MG_REASON_ACTIVATION_FAILED,
    MG_REASON_NET_RELEASED,
    MG_REASON_CONDITIONS_MET,
} mg_reason_t;

const char *mg_reason_str(mg_reason_t reason);

/*
 * Injected side-effect layer.  Open order is netif_start -> napt_enable ->
 * proxy_start; close order is the strict reverse proxy_stop -> napt_disable ->
 * netif_stop.  Every callback must be idempotent on the device side.  Any of
 * the callbacks may be NULL, in which case the gate treats it as a no-op success
 * (used by the safe profile and by host tests that only exercise a subset).
 */
typedef struct {
    mg_err_t (*netif_start)(void *ctx);
    mg_err_t (*napt_enable)(void *ctx);
    mg_err_t (*proxy_start)(void *ctx);
    void (*proxy_stop)(void *ctx);
    void (*napt_disable)(void *ctx);
    void (*netif_stop)(void *ctx);
    /* Optional marker emitter; receives a fully-formed, newline-free line such
     * as "BOOTMUX_PATH_CLOSED reason=LEASE_EXPIRED".  May be NULL. */
    void (*emit)(const char *line, void *ctx);
    void *ctx;
} mg_actions_t;

typedef struct {
    /* The four gate inputs. */
    bool wifi_has_ip;
    bool target_reachable;
    bool allowlist_loaded;
    /* Absolute lease deadline in milliseconds (same clock as now_ms passed to
     * mg_reconcile / mg_lease_active).  0 == lease absent. */
    int64_t lease_deadline_ms;
    /* Output state. */
    bool path_open;
    mg_reason_t last_reason;
    /* Last close reason surfaced via mg_close_reason_changed(); used to emit one
     * marker per distinct failing condition while staying closed. */
    mg_reason_t emitted_close_reason;
} mg_state_t;

/* Reset to the boot state: everything false, lease absent, path closed,
 * reason BOOT.  Does not emit markers. */
void mg_init(mg_state_t *state);

/*
 * Grant or renew the management lease.  ttl_seconds outside [10,60] is rejected
 * (returns false) and leaves state untouched.  On success the absolute deadline
 * is set to now_ms + ttl_seconds*1000.  There is no initial lease and no
 * auto-grant: this is the only way the lease becomes active.
 */
bool mg_lease_grant(mg_state_t *state, int ttl_seconds, int64_t now_ms);

/* Explicitly drop the lease (NET_RELEASE / WIFI_CLEAR / BLE disconnect). */
void mg_lease_release(mg_state_t *state);

/* True iff a lease is present and now_ms is strictly before its deadline. */
bool mg_lease_active(const mg_state_t *state, int64_t now_ms);

/* The single open predicate: all four conditions simultaneously. */
bool mg_should_open(const mg_state_t *state, int64_t now_ms);

/*
 * Reconcile the path against the current conditions.
 *
 *   false -> true : run netif_start, napt_enable, proxy_start in order; only
 *                   mark OPEN after all succeed.  Any failure rolls back the
 *                   already-applied steps in reverse and records ACTIVATION_FAILED.
 *   true  -> false: run proxy_stop, napt_disable, netif_stop in reverse and
 *                   record the caller-supplied reason.
 *   no transition : state is left untouched (last_reason is NOT overwritten),
 *                   and no marker is emitted.  Use mg_close_reason_changed() to
 *                   detect a change in the failing condition while staying closed.
 *
 * `reason` is the trigger the caller observed (BOOT, WIFI_DISCONNECTED, ...).
 * Returns true iff this call caused an open<->closed transition.
 */
bool mg_reconcile(mg_state_t *state, int64_t now_ms, mg_reason_t reason,
                  const mg_actions_t *actions);

/*
 * True iff the path is currently closed and the reason it is closed differs
 * from the last reason recorded by a call to this function.  Calling it with
 * the current reason updates the internal marker, so a caller can emit a single
 * "BOOTMUX_PATH_CLOSED reason=..." line per distinct failing condition without
 * spamming on every reconcile tick.  Returns false while the path is open.
 */
bool mg_close_reason_changed(mg_state_t *state, mg_reason_t reason);

#ifdef __cplusplus
}
#endif
