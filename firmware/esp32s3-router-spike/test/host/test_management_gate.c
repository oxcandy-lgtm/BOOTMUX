/*
 * BOOTMUX R7C-P1 S3 — host unit tests for the pure management-path cores.
 *
 * Compiles with a bare host toolchain (no ESP-IDF): management_gate.c and
 * target_probe.c are deliberately dependency-free so the gate truth table
 * (T1..T16) can be proven off-device.  Run:
 *
 *   cc -std=c11 -Wall -Wextra -I main test/host/test_management_gate.c \
 *      main/management_gate.c main/target_probe.c -o /tmp/bmx_gate_test \
 *      && /tmp/bmx_gate_test
 */

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "management_gate.h"
#include "target_probe.h"

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_checks;                                                            \
        if (!(cond)) {                                                         \
            ++g_failures;                                                      \
            printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);           \
        }                                                                      \
    } while (0)

#define CHECK_EQ_INT(a, b)                                                     \
    do {                                                                       \
        ++g_checks;                                                            \
        long _a = (long)(a), _b = (long)(b);                                   \
        if (_a != _b) {                                                        \
            ++g_failures;                                                      \
            printf("  FAIL %s:%d  %s == %s (%ld != %ld)\n", __FILE__,          \
                   __LINE__, #a, #b, _a, _b);                                  \
        }                                                                      \
    } while (0)

#define CHECK_STR(a, b)                                                        \
    do {                                                                       \
        ++g_checks;                                                            \
        if (strcmp((a), (b)) != 0) {                                           \
            ++g_failures;                                                      \
            printf("  FAIL %s:%d  \"%s\" != \"%s\"\n", __FILE__, __LINE__,     \
                   (a), (b));                                                  \
        }                                                                      \
    } while (0)

/* ---- recording action stub ------------------------------------------------ */

enum {
    OP_NETIF_START,
    OP_NAPT_ENABLE,
    OP_PROXY_START,
    OP_PROXY_STOP,
    OP_NAPT_DISABLE,
    OP_NETIF_STOP,
    OP_MAX,
};

typedef struct {
    int order[16];
    int count;
    /* which open step should fail, -1 == none */
    int fail_at;
    int calls;
    char last_marker[80];
    int marker_count;
} rec_t;

static void rec_reset(rec_t *r) { memset(r, 0, sizeof(*r)); r->fail_at = -1; }

static mg_err_t rec_netif_start(void *ctx) {
    rec_t *r = ctx; r->order[r->count++] = OP_NETIF_START;
    return (r->fail_at == OP_NETIF_START) ? MG_FAIL : MG_OK;
}
static mg_err_t rec_napt_enable(void *ctx) {
    rec_t *r = ctx; r->order[r->count++] = OP_NAPT_ENABLE;
    return (r->fail_at == OP_NAPT_ENABLE) ? MG_FAIL : MG_OK;
}
static mg_err_t rec_proxy_start(void *ctx) {
    rec_t *r = ctx; r->order[r->count++] = OP_PROXY_START;
    return (r->fail_at == OP_PROXY_START) ? MG_FAIL : MG_OK;
}
static void rec_proxy_stop(void *ctx) { rec_t *r = ctx; r->order[r->count++] = OP_PROXY_STOP; }
static void rec_napt_disable(void *ctx) { rec_t *r = ctx; r->order[r->count++] = OP_NAPT_DISABLE; }
static void rec_netif_stop(void *ctx) { rec_t *r = ctx; r->order[r->count++] = OP_NETIF_STOP; }
static void rec_emit(const char *line, void *ctx) {
    rec_t *r = ctx;
    snprintf(r->last_marker, sizeof(r->last_marker), "%s", line);
    ++r->marker_count;
}

static mg_actions_t make_actions(rec_t *r) {
    mg_actions_t a = {0};
    a.netif_start = rec_netif_start;
    a.napt_enable = rec_napt_enable;
    a.proxy_start = rec_proxy_start;
    a.proxy_stop = rec_proxy_stop;
    a.napt_disable = rec_napt_disable;
    a.netif_stop = rec_netif_stop;
    a.emit = rec_emit;
    a.ctx = r;
    return a;
}

/* Fill all four conditions so the gate should open. */
static void fill_conditions(mg_state_t *s, int64_t now) {
    s->wifi_has_ip = true;
    s->target_reachable = true;
    s->allowlist_loaded = true;
    CHECK(mg_lease_grant(s, 60, now));
}

/* ---- T1: boot state is fail-closed --------------------------------------- */
static void test_t1_boot_closed(void) {
    printf("T1 boot state fail-closed\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    CHECK(!s.path_open);
    CHECK(!mg_should_open(&s, 0));
    CHECK(!mg_reconcile(&s, 0, MG_REASON_BOOT, &a));
    CHECK(!s.path_open);
    CHECK_EQ_INT(r.count, 0);          /* no side effects at boot */
    CHECK_EQ_INT(r.marker_count, 0);   /* reconcile emits nothing on no-transition */
    CHECK_STR(mg_reason_str(s.last_reason), "BOOT");
}

/* ---- T2: all four conditions -> open, marker emitted --------------------- */
static void test_t2_all_four_opens(void) {
    printf("T2 all four conditions open the path\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    CHECK(mg_should_open(&s, 1000));
    CHECK(mg_reconcile(&s, 1000, MG_REASON_CONDITIONS_MET, &a));
    CHECK(s.path_open);
    /* open order must be netif -> napt -> proxy */
    CHECK_EQ_INT(r.count, 3);
    CHECK_EQ_INT(r.order[0], OP_NETIF_START);
    CHECK_EQ_INT(r.order[1], OP_NAPT_ENABLE);
    CHECK_EQ_INT(r.order[2], OP_PROXY_START);
    CHECK_STR(r.last_marker, "BOOTMUX_PATH_OPEN");
    CHECK_STR(mg_reason_str(s.last_reason), "CONDITIONS_MET");
}

/* ---- T3..T6: each single missing condition keeps it closed --------------- */
static void test_t3_no_wifi_ip(void) {
    printf("T3 missing wifi_has_ip stays closed\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    s.wifi_has_ip = false;
    CHECK(!mg_should_open(&s, 1000));
    CHECK(!mg_reconcile(&s, 1000, MG_REASON_WIFI_NO_IP, &a));
    CHECK(!s.path_open);
    CHECK_EQ_INT(r.count, 0);
}

static void test_t4_target_unreachable(void) {
    printf("T4 missing target_reachable stays closed\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    s.target_reachable = false;
    CHECK(!mg_should_open(&s, 1000));
    CHECK(!mg_reconcile(&s, 1000, MG_REASON_TARGET_UNREACHABLE, &a));
    CHECK(!s.path_open);
}

static void test_t5_allowlist_not_loaded(void) {
    printf("T5 missing allowlist_loaded stays closed\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    s.allowlist_loaded = false;
    CHECK(!mg_should_open(&s, 1000));
    CHECK(!mg_reconcile(&s, 1000, MG_REASON_TARGET_UNREACHABLE, &a));
    CHECK(!s.path_open);
}

static void test_t6_lease_absent(void) {
    printf("T6 absent lease stays closed\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    s.wifi_has_ip = true;
    s.target_reachable = true;
    s.allowlist_loaded = true;
    /* no lease grant */
    CHECK(!mg_lease_active(&s, 1000));
    CHECK(!mg_should_open(&s, 1000));
    CHECK(!mg_reconcile(&s, 1000, MG_REASON_LEASE_ABSENT, &a));
    CHECK(!s.path_open);
}

/* ---- T7: lease TTL bounds ------------------------------------------------ */
static void test_t7_lease_bounds(void) {
    printf("T7 lease ttl bounds [10,60]\n");
    mg_state_t s; mg_init(&s);
    CHECK(!mg_lease_grant(&s, 9, 0));    /* below min */
    CHECK(!mg_lease_grant(&s, 61, 0));   /* above max */
    CHECK_EQ_INT(s.lease_deadline_ms, 0);
    CHECK(mg_lease_grant(&s, 10, 0));
    CHECK_EQ_INT(s.lease_deadline_ms, 10000);
    CHECK(mg_lease_grant(&s, 60, 5000));
    CHECK_EQ_INT(s.lease_deadline_ms, 65000);
}

/* ---- T8: lease active window and expiry ---------------------------------- */
static void test_t8_lease_window(void) {
    printf("T8 lease active until deadline, expired after\n");
    mg_state_t s; mg_init(&s);
    CHECK(mg_lease_grant(&s, 60, 1000));
    CHECK(mg_lease_active(&s, 1000));
    CHECK(mg_lease_active(&s, 60999));
    CHECK(!mg_lease_active(&s, 61000));  /* strictly before deadline */
    CHECK(!mg_lease_active(&s, 70000));
}

/* ---- T9: open -> condition drops -> reverse-order teardown --------------- */
static void test_t9_reverse_teardown(void) {
    printf("T9 withdrawal runs proxy,napt,netif in reverse\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    CHECK(mg_reconcile(&s, 1000, MG_REASON_CONDITIONS_MET, &a));
    CHECK(s.path_open);
    r.count = 0;
    s.wifi_has_ip = false;
    CHECK(mg_reconcile(&s, 2000, MG_REASON_WIFI_DISCONNECTED, &a));
    CHECK(!s.path_open);
    CHECK_EQ_INT(r.count, 3);
    CHECK_EQ_INT(r.order[0], OP_PROXY_STOP);
    CHECK_EQ_INT(r.order[1], OP_NAPT_DISABLE);
    CHECK_EQ_INT(r.order[2], OP_NETIF_STOP);
    CHECK_STR(r.last_marker, "BOOTMUX_PATH_CLOSED reason=WIFI_DISCONNECTED");
}

/* ---- T10: activation failure rolls back applied steps in reverse --------- */
static void test_t10_activation_rollback(void) {
    printf("T10 proxy_start failure rolls back napt+netif\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    r.fail_at = OP_PROXY_START;
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    CHECK(mg_reconcile(&s, 1000, MG_REASON_CONDITIONS_MET, &a));
    CHECK(!s.path_open);                 /* must NOT open */
    CHECK_STR(mg_reason_str(s.last_reason), "ACTIVATION_FAILED");
    /* sequence: netif_start, napt_enable, proxy_start(fail), napt_disable, netif_stop */
    CHECK_EQ_INT(r.count, 5);
    CHECK_EQ_INT(r.order[0], OP_NETIF_START);
    CHECK_EQ_INT(r.order[1], OP_NAPT_ENABLE);
    CHECK_EQ_INT(r.order[2], OP_PROXY_START);
    CHECK_EQ_INT(r.order[3], OP_NAPT_DISABLE);
    CHECK_EQ_INT(r.order[4], OP_NETIF_STOP);
    CHECK_STR(r.last_marker, "BOOTMUX_PATH_CLOSED reason=ACTIVATION_FAILED");
}

/* ---- T11: lease expiry while open closes with LEASE_EXPIRED -------------- */
static void test_t11_lease_expiry_closes(void) {
    printf("T11 lease expiry withdraws the open path\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);            /* deadline 61000 */
    CHECK(mg_reconcile(&s, 1000, MG_REASON_CONDITIONS_MET, &a));
    CHECK(s.path_open);
    r.count = 0;
    CHECK(mg_reconcile(&s, 61000, MG_REASON_LEASE_EXPIRED, &a));
    CHECK(!s.path_open);
    CHECK_STR(r.last_marker, "BOOTMUX_PATH_CLOSED reason=LEASE_EXPIRED");
}

/* ---- T12: NET_RELEASE while open closes with NET_RELEASED ---------------- */
static void test_t12_net_release(void) {
    printf("T12 NET_RELEASE withdraws the open path\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    CHECK(mg_reconcile(&s, 1000, MG_REASON_CONDITIONS_MET, &a));
    mg_lease_release(&s);
    r.count = 0;
    CHECK(mg_reconcile(&s, 2000, MG_REASON_NET_RELEASED, &a));
    CHECK(!s.path_open);
    CHECK_STR(r.last_marker, "BOOTMUX_PATH_CLOSED reason=NET_RELEASED");
}

/* ---- T13: BLE disconnect closes with BLE_DISCONNECTED -------------------- */
static void test_t13_ble_disconnect(void) {
    printf("T13 BLE disconnect withdraws the open path\n");
    mg_state_t s; mg_init(&s);
    rec_t r; rec_reset(&r);
    mg_actions_t a = make_actions(&r);
    fill_conditions(&s, 1000);
    CHECK(mg_reconcile(&s, 1000, MG_REASON_CONDITIONS_MET, &a));
    mg_lease_release(&s);
    r.count = 0;
    CHECK(mg_reconcile(&s, 2000, MG_REASON_BLE_DISCONNECTED, &a));
    CHECK(!s.path_open);
    CHECK_STR(r.last_marker, "BOOTMUX_PATH_CLOSED reason=BLE_DISCONNECTED");
}

/* ---- T14: close_reason_changed emits once per distinct reason ------------ */
static void test_t14_reason_dedup(void) {
    printf("T14 close reason marker emitted once per distinct condition\n");
    mg_state_t s; mg_init(&s);
    /* boot sets emitted_close_reason = BOOT */
    CHECK(mg_close_reason_changed(&s, MG_REASON_LEASE_ABSENT));  /* first time */
    CHECK(!mg_close_reason_changed(&s, MG_REASON_LEASE_ABSENT)); /* same -> no */
    CHECK(mg_close_reason_changed(&s, MG_REASON_WIFI_NO_IP));    /* changed */
    CHECK(!mg_close_reason_changed(&s, MG_REASON_WIFI_NO_IP));
    /* while open it never reports a change */
    s.path_open = true;
    CHECK(!mg_close_reason_changed(&s, MG_REASON_TARGET_UNREACHABLE));
}

/* ---- T15: probe reachability rules (3 up / 2 down / 15s decay) ----------- */
static void test_t15_probe_rules(void) {
    printf("T15 probe 3-success / 2-failure / 15s decay\n");
    tp_state_t p; tp_init(&p);
    /* probing forbidden before a subnet is set */
    CHECK(!tp_probe_allowed(&p));
    CHECK_EQ_INT(tp_select_target(&p), 0);

    tp_set_subnet(&p, tp_ipv4(192, 168, 11, 50), tp_ipv4(255, 255, 255, 0));
    CHECK(tp_allowlist_loaded(&p));
    CHECK(tp_probe_allowed(&p));
    CHECK_EQ_INT(tp_select_target(&p), tp_ipv4(192, 168, 11, 1));

    /* 2 successes not yet reachable, 3rd makes it reachable */
    tp_record_result(&p, true, 1000);
    CHECK(!tp_is_reachable(&p, 1000));
    tp_record_result(&p, true, 2000);
    CHECK(!tp_is_reachable(&p, 2000));
    tp_record_result(&p, true, 3000);
    CHECK(tp_is_reachable(&p, 3000));

    /* a single failure does not drop it; two consecutive do */
    tp_record_result(&p, false, 4000);
    CHECK(tp_is_reachable(&p, 4000));
    tp_record_result(&p, false, 5000);
    CHECK(!tp_is_reachable(&p, 5000));

    /* back to reachable, then 15s with no result decays it */
    tp_record_result(&p, true, 6000);
    tp_record_result(&p, true, 7000);
    tp_record_result(&p, true, 8000);
    CHECK(tp_is_reachable(&p, 8000));
    CHECK(tp_is_reachable(&p, 8000 + 14999));
    CHECK(!tp_is_reachable(&p, 8000 + 15000));
}

/* ---- T16: allowlist subnet gating ---------------------------------------- */
static void test_t16_allowlist_subnet(void) {
    printf("T16 allowlist only matches the STA subnet\n");
    tp_state_t p; tp_init(&p);
    /* unknown router subnet -> allowlist not loaded, no target */
    tp_set_subnet(&p, tp_ipv4(10, 0, 0, 5), tp_ipv4(255, 255, 255, 0));
    CHECK(!tp_allowlist_loaded(&p));
    CHECK(!tp_probe_allowed(&p));
    CHECK_EQ_INT(tp_select_target(&p), 0);

    /* second allowlist entry subnet */
    tp_set_subnet(&p, tp_ipv4(192, 168, 77, 20), tp_ipv4(255, 255, 255, 0));
    CHECK(tp_allowlist_loaded(&p));
    CHECK_EQ_INT(tp_select_target(&p), tp_ipv4(192, 168, 77, 1));

    /* clearing the subnet (disconnect) drops everything */
    tp_set_subnet(&p, 0, 0);
    CHECK(!tp_allowlist_loaded(&p));
    CHECK(!tp_probe_allowed(&p));
    CHECK(!tp_is_reachable(&p, 999999));
}

int main(void) {
    test_t1_boot_closed();
    test_t2_all_four_opens();
    test_t3_no_wifi_ip();
    test_t4_target_unreachable();
    test_t5_allowlist_not_loaded();
    test_t6_lease_absent();
    test_t7_lease_bounds();
    test_t8_lease_window();
    test_t9_reverse_teardown();
    test_t10_activation_rollback();
    test_t11_lease_expiry_closes();
    test_t12_net_release();
    test_t13_ble_disconnect();
    test_t14_reason_dedup();
    test_t15_probe_rules();
    test_t16_allowlist_subnet();

    printf("\n%d checks, %d failures\n", g_checks, g_failures);
    if (g_failures == 0) {
        printf("ALL_GATE_TESTS_PASS\n");
        return 0;
    }
    printf("GATE_TESTS_FAILED\n");
    return 1;
}
