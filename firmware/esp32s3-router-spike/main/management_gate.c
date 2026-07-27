#include "management_gate.h"

#include <stdio.h>

const char *mg_reason_str(mg_reason_t reason) {
    switch (reason) {
        case MG_REASON_BOOT: return "BOOT";
        case MG_REASON_WIFI_NO_IP: return "WIFI_NO_IP";
        case MG_REASON_WIFI_DISCONNECTED: return "WIFI_DISCONNECTED";
        case MG_REASON_TARGET_UNREACHABLE: return "TARGET_UNREACHABLE";
        case MG_REASON_LEASE_ABSENT: return "LEASE_ABSENT";
        case MG_REASON_LEASE_EXPIRED: return "LEASE_EXPIRED";
        case MG_REASON_BLE_DISCONNECTED: return "BLE_DISCONNECTED";
        case MG_REASON_WIFI_CLEARED: return "WIFI_CLEARED";
        case MG_REASON_ACTIVATION_FAILED: return "ACTIVATION_FAILED";
        case MG_REASON_NET_RELEASED: return "NET_RELEASED";
        case MG_REASON_CONDITIONS_MET: return "CONDITIONS_MET";
    }
    return "BOOT";
}

void mg_init(mg_state_t *state) {
    if (!state) return;
    state->wifi_has_ip = false;
    state->target_reachable = false;
    state->allowlist_loaded = false;
    state->lease_deadline_ms = 0;
    state->path_open = false;
    state->last_reason = MG_REASON_BOOT;
    state->emitted_close_reason = MG_REASON_BOOT;
}

bool mg_lease_grant(mg_state_t *state, int ttl_seconds, int64_t now_ms) {
    if (!state) return false;
    if (ttl_seconds < MG_LEASE_TTL_MIN || ttl_seconds > MG_LEASE_TTL_MAX) return false;
    state->lease_deadline_ms = now_ms + (int64_t)ttl_seconds * 1000;
    return true;
}

void mg_lease_release(mg_state_t *state) {
    if (!state) return;
    state->lease_deadline_ms = 0;
}

bool mg_lease_active(const mg_state_t *state, int64_t now_ms) {
    if (!state) return false;
    return state->lease_deadline_ms != 0 && now_ms < state->lease_deadline_ms;
}

bool mg_should_open(const mg_state_t *state, int64_t now_ms) {
    if (!state) return false;
    return state->wifi_has_ip && state->target_reachable &&
           state->allowlist_loaded && mg_lease_active(state, now_ms);
}

static void emit_marker(const mg_actions_t *actions, bool open, mg_reason_t reason) {
    if (!actions || !actions->emit) return;
    char line[64];
    if (open) {
        snprintf(line, sizeof(line), "BOOTMUX_PATH_OPEN");
    } else {
        snprintf(line, sizeof(line), "BOOTMUX_PATH_CLOSED reason=%s", mg_reason_str(reason));
    }
    actions->emit(line, actions->ctx);
}

/* Run the open sequence; on first failure roll back applied steps in reverse. */
static bool activate(mg_state_t *state, const mg_actions_t *actions) {
    int applied = 0; /* number of successfully applied open steps */
    mg_err_t err = MG_OK;

    if (actions && actions->netif_start) {
        err = actions->netif_start(actions->ctx);
        if (err == MG_OK) applied = 1;
    } else {
        applied = 1;
    }

    if (applied >= 1) {
        if (actions && actions->napt_enable) {
            err = actions->napt_enable(actions->ctx);
            if (err == MG_OK) applied = 2;
        } else {
            applied = 2;
        }
    }

    if (applied >= 2) {
        if (actions && actions->proxy_start) {
            err = actions->proxy_start(actions->ctx);
            if (err == MG_OK) applied = 3;
        } else {
            applied = 3;
        }
    }

    if (applied == 3) {
        state->path_open = true;
        state->last_reason = MG_REASON_CONDITIONS_MET;
        emit_marker(actions, true, MG_REASON_CONDITIONS_MET);
        return true;
    }

    /* Roll back whatever was applied, in strict reverse order. */
    if (applied >= 2 && actions && actions->napt_disable) actions->napt_disable(actions->ctx);
    if (applied >= 1 && actions && actions->netif_stop) actions->netif_stop(actions->ctx);
    state->path_open = false;
    state->last_reason = MG_REASON_ACTIVATION_FAILED;
    emit_marker(actions, false, MG_REASON_ACTIVATION_FAILED);
    return false;
}

static void deactivate(mg_state_t *state, const mg_actions_t *actions, mg_reason_t reason) {
    if (actions && actions->proxy_stop) actions->proxy_stop(actions->ctx);
    if (actions && actions->napt_disable) actions->napt_disable(actions->ctx);
    if (actions && actions->netif_stop) actions->netif_stop(actions->ctx);
    state->path_open = false;
    state->last_reason = reason;
    emit_marker(actions, false, reason);
}

bool mg_reconcile(mg_state_t *state, int64_t now_ms, mg_reason_t reason,
                  const mg_actions_t *actions) {
    if (!state) return false;
    bool should_open = mg_should_open(state, now_ms);

    if (should_open && !state->path_open) {
        activate(state, actions);
        return true; /* transition attempted (OPEN or rolled-back ACTIVATION_FAILED) */
    }
    if (!should_open && state->path_open) {
        deactivate(state, actions, reason);
        return true; /* transition: open -> closed */
    }
    /* No transition: leave last_reason untouched, emit nothing. */
    return false;
}

bool mg_close_reason_changed(mg_state_t *state, mg_reason_t reason) {
    if (!state || state->path_open) return false;
    if (reason == state->emitted_close_reason) return false;
    state->emitted_close_reason = reason;
    state->last_reason = reason;
    return true;
}
