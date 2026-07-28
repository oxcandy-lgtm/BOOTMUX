#!/usr/bin/env python3
"""R7C P3 — mutation tests for scripts/check-contract-sync.py.

Proves the checker KILLS representative broken variants (M01–M12) rather than
only passing the current tree.  Every test feeds in-memory fixture text to the
pure checker helpers; nothing touches the developer Mac network state and no
temporary file is written outside this module.

M01 is the inverse case: a whitespace-only README reflow must still PASS,
proving the whitespace-robust normalization does not false-negative.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

# Load the hyphenated checker module in-process.
_CHECKER_PATH = Path(__file__).resolve().parents[1] / "check-contract-sync.py"
_spec = importlib.util.spec_from_file_location("check_contract_sync", _CHECKER_PATH)
assert _spec is not None and _spec.loader is not None, f"cannot load checker: {_CHECKER_PATH}"
checker = importlib.util.module_from_spec(_spec)
sys.modules["check_contract_sync"] = checker
_spec.loader.exec_module(checker)


# ---------------------------------------------------------------------------
# Minimal "good" fixtures — just enough to satisfy each pure contract function.
# ---------------------------------------------------------------------------

GOOD_README = """
# Router spike

The normal build is now **USB HID-only**. Plugging the ESP32-S3 into a Mac must
not enumerate a USB Ethernet interface, start a DHCP exchange, publish a DNS
server, or offer a default route.

The experimental interface:
- does **not** run a DHCP server;
- has no configured gateway;
- does not provide DNS;
"""

GOOD_SAFE_SDKCONFIG = """
CONFIG_TINYUSB_NET_MODE_NONE=y
# CONFIG_TINYUSB_NET_MODE_NCM is not set
# CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL is not set
# CONFIG_LWIP_IP_FORWARD is not set
# CONFIG_LWIP_IPV4_NAPT is not set
"""

GOOD_DESCRIPTORS = """
#define BOOTMUX_USB_PRODUCT "BOOTMUX Keyboard Safe"
#define BOOTMUX_USB_SERIAL "BOOTMUX-HID-SAFE"
"""

GOOD_USB_ROUTER = """
    .gw = { .addr = 0 },
    puts("BOOTMUX_USB_NETWORK_NO_DHCP_NO_DEFAULT_ROUTE");
    puts("BOOTMUX_USB_NETIF_DOWN_AT_BOOT_EXPERIMENTAL");
    puts("BOOTMUX_USB_NETWORK_SAFE_OFF");
"""

GOOD_EXP_SDKCONFIG = "CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL=y\n"

GOOD_MGMT_C = """
bool mg_should_open(const mg_state_t *state, int64_t now_ms) {
    return state->wifi_has_ip && state->target_reachable &&
           state->allowlist_loaded && mg_lease_active(state, now_ms);
}
bool mg_lease_grant(mg_state_t *state, int ttl_seconds, int64_t now_ms) {
    if (ttl_seconds < MG_LEASE_TTL_MIN || ttl_seconds > MG_LEASE_TTL_MAX) return false;
    state->lease_deadline_ms = now_ms + (int64_t)ttl_seconds * 1000;
    return true;
}
static void deactivate(mg_state_t *state, const mg_actions_t *actions, mg_reason_t reason) {
    if (actions && actions->proxy_stop) actions->proxy_stop(actions->ctx);
    if (actions && actions->napt_disable) actions->napt_disable(actions->ctx);
    if (actions && actions->netif_stop) actions->netif_stop(actions->ctx);
}
void mg_init(mg_state_t *state) {
    state->path_open = false;
    state->last_reason = MG_REASON_BOOT;
}
"""

GOOD_MGMT_H = """
#define MG_LEASE_TTL_MIN 10
#define MG_LEASE_TTL_MAX 60
"""

GOOD_PROBE_C = """
static const uint32_t kAllowlist[] = {
    TP_IPV4(192, 168, 11, 1),
    TP_IPV4(192, 168, 77, 1),
};
"""

GOOD_RUNTIME_C = """
static void wifi_task(void *arg) {
    if (event.event_id == WIFI_EVENT_STA_DISCONNECTED) {
        reconcile_management_path(MG_REASON_WIFI_DISCONNECTED);
    } else if (event.event_id == IP_EVENT_STA_GOT_IP) {
        s_gate.wifi_has_ip = true;
        reconcile_management_path(MG_REASON_BOOT);
    }
}
void handle_ble(const char *cmd) {
    if (strcmp(cmd, "NET_RELEASE") == 0) { mg_lease_release(&s_gate); }
    if (strcmp(cmd, "WIFI_CLEAR") == 0) { mg_lease_release(&s_gate); }
}
"""

GOOD_GUARDIAN_PY = """
def prove_identity(host):
    # ambiguous identity fails closed into audit-only
    return IdentityResult(proven=False, ambiguous=True, reason="audit-only")

class StateStore:
    def validate(self):
        if os.path.islink(path): raise StateStoreError("symlink")
        if (st.st_mode & 0o777) != 0o700: raise StateStoreError("mode")
        if st.st_uid != 0: raise StateStoreError("owner")
        if data.get("schema_version") != SCHEMA_VERSION: raise StateStoreError("schema")

def redact_baseline(baseline):
    wifi["associated_ssid"] = "<redacted>"
    return baseline

def plan_r6_wifi_toggle(host):
    # last resort with bounded cooldown
    if cooldown_active(host): return skip
"""


class TestWhitespaceRobustReadme(unittest.TestCase):
    """M01 / M02 — README prose contract."""

    def test_M01_whitespace_reflow_still_passes(self):
        # Reflow the same accurate prose with arbitrary line breaks + bold.
        reflowed = (
            "The normal build is now **USB\nHID-only**. Plugging the ESP32-S3\n"
            "into a Mac must\n\nnot enumerate a USB Ethernet interface.\n"
            "It does **not** run a DHCP server, has no configured gateway,\n"
            "and does not provide DNS.\n"
        )
        self.assertEqual(checker.r7c_readme_errors(reflowed), [],
                         "M01: whitespace-only reflow of accurate prose must still pass")

    def test_M02_safety_statement_removed_fails(self):
        mutant = GOOD_README.replace("must\nnot enumerate a USB Ethernet interface",
                                     "may enumerate a USB Ethernet interface")
        errors = checker.r7c_readme_errors(mutant)
        self.assertTrue(any("USB Ethernet interface" in e for e in errors),
                        "M02: removing the no-USB-Ethernet statement must be caught")


class TestSafeDefault(unittest.TestCase):
    """M03 — safe sdkconfig must stay HID-only."""

    def test_M03_safe_sdkconfig_ncm_enabled_fails(self):
        mutant = GOOD_SAFE_SDKCONFIG.replace(
            "# CONFIG_TINYUSB_NET_MODE_NCM is not set",
            "CONFIG_TINYUSB_NET_MODE_NCM=y")
        errors = checker.r7c_safe_default_errors(mutant, GOOD_DESCRIPTORS, GOOD_USB_ROUTER)
        self.assertTrue(any("NCM" in e for e in errors),
                        "M03: enabling NCM in the safe sdkconfig must be caught")

    def test_safe_default_good_passes(self):
        self.assertEqual(
            checker.r7c_safe_default_errors(GOOD_SAFE_SDKCONFIG, GOOD_DESCRIPTORS, GOOD_USB_ROUTER),
            [])


class TestExperimental(unittest.TestCase):
    """M04 — experimental profile must not reintroduce a DHCP server."""

    def test_M04_dhcp_server_reintroduced_fails(self):
        mutant = GOOD_USB_ROUTER + "\n    .flags = ESP_NETIF_DHCP_SERVER,\n"
        errors = checker.r7c_experimental_errors(mutant, GOOD_EXP_SDKCONFIG, GOOD_RUNTIME_C)
        self.assertTrue(any("DHCP server" in e for e in errors),
                        "M04: reintroducing a DHCP server must be caught")

    def test_experimental_good_passes(self):
        self.assertEqual(
            checker.r7c_experimental_errors(GOOD_USB_ROUTER, GOOD_EXP_SDKCONFIG, GOOD_RUNTIME_C),
            [])


class TestP1Gate(unittest.TestCase):
    """M05–M08 — four-condition gate, lease bound, allowlist, teardown order."""

    def test_gate_good_passes(self):
        self.assertEqual(
            checker.r7c_p1_gate_errors(GOOD_MGMT_C, GOOD_MGMT_H, GOOD_PROBE_C, GOOD_RUNTIME_C),
            [])

    def test_M05_one_gate_condition_removed_fails(self):
        mutant = GOOD_MGMT_C.replace("state->target_reachable &&\n           ", "")
        errors = checker.r7c_p1_gate_errors(mutant, GOOD_MGMT_H, GOOD_PROBE_C, GOOD_RUNTIME_C)
        self.assertTrue(any("target_reachable" in e for e in errors),
                        "M05: removing a gate condition from mg_should_open must be caught")

    def test_M06_lease_bound_raised_fails(self):
        mutant_h = GOOD_MGMT_H.replace("#define MG_LEASE_TTL_MAX 60", "#define MG_LEASE_TTL_MAX 600")
        errors = checker.r7c_p1_gate_errors(GOOD_MGMT_C, mutant_h, GOOD_PROBE_C, GOOD_RUNTIME_C)
        self.assertTrue(any("60 seconds" in e for e in errors),
                        "M06: raising the lease TTL bound above 60s must be caught")

    def test_M07_allowlist_widened_fails(self):
        mutant = GOOD_PROBE_C + "    TP_IPV4(10, 0, 0, 1),\n"
        errors = checker.r7c_p1_gate_errors(GOOD_MGMT_C, GOOD_MGMT_H, mutant, GOOD_RUNTIME_C)
        self.assertTrue(any("allowlist" in e for e in errors),
                        "M07: widening the target allowlist must be caught")

    def test_M08_teardown_order_changed_fails(self):
        mutant = GOOD_MGMT_C.replace(
            "    if (actions && actions->proxy_stop) actions->proxy_stop(actions->ctx);\n"
            "    if (actions && actions->napt_disable) actions->napt_disable(actions->ctx);\n"
            "    if (actions && actions->netif_stop) actions->netif_stop(actions->ctx);",
            "    if (actions && actions->netif_stop) actions->netif_stop(actions->ctx);\n"
            "    if (actions && actions->napt_disable) actions->napt_disable(actions->ctx);\n"
            "    if (actions && actions->proxy_stop) actions->proxy_stop(actions->ctx);")
        errors = checker.r7c_p1_gate_errors(mutant, GOOD_MGMT_H, GOOD_PROBE_C, GOOD_RUNTIME_C)
        self.assertTrue(any("teardown order" in e for e in errors),
                        "M08: changing teardown order away from proxy->NAPT->netif must be caught")


class TestP2Guardian(unittest.TestCase):
    """M09–M12 — Guardian destructive-op and redaction contracts."""

    def test_guardian_good_passes(self):
        self.assertEqual(checker.r7c_p2_guardian_errors(GOOD_GUARDIAN_PY), [])

    def test_M09_global_route_flush_added_fails(self):
        mutant = GOOD_GUARDIAN_PY + '\n    run(["route", "-f"])\n'
        errors = checker.r7c_p2_guardian_errors(mutant)
        self.assertTrue(any("routing-table flush" in e for e in errors),
                        "M09: adding a global route flush must be caught")

    def test_M10_service_deletion_added_fails(self):
        mutant = GOOD_GUARDIAN_PY + '\n    run(["networksetup", "-removenetworkservice", name])\n'
        errors = checker.r7c_p2_guardian_errors(mutant)
        self.assertTrue(any("delete a network service" in e for e in errors),
                        "M10: adding network-service deletion must be caught")

    def test_M11_ambiguous_identity_mutation_enabled_fails(self):
        mutant = GOOD_GUARDIAN_PY.replace("audit-only", "mutate-anyway")
        errors = checker.r7c_p2_guardian_errors(mutant)
        self.assertTrue(any("audit-only" in e for e in errors),
                        "M11: letting ambiguous identity mutate must be caught")

    def test_M12_ssid_redaction_removed_fails(self):
        mutant = GOOD_GUARDIAN_PY.replace('wifi["associated_ssid"] = "<redacted>"',
                                          'wifi["associated_ssid"] = baseline_ssid')
        errors = checker.r7c_p2_guardian_errors(mutant)
        self.assertTrue(any("redaction" in e for e in errors),
                        "M12: removing SSID redaction must be caught")


if __name__ == "__main__":
    unittest.main(verbosity=2)
