#!/usr/bin/env python3
"""Deterministic, fixture-driven tests for the BOOTMUX macOS network guardian.

Every test runs against :class:`FakeHost` — the developer Mac is NEVER mutated.
Tests assert the EXACT command plan (argv) and forbid any command that targets
an unrelated interface or service.

Run:  python3 -m unittest discover -s scripts/macos/tests -v
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Load the hyphenated module by path.
GUARDIAN_PATH = Path(__file__).resolve().parents[1] / "bootmux-network-guardian.py"
_spec = importlib.util.spec_from_file_location("bootmux_network_guardian", GUARDIAN_PATH)
assert _spec is not None and _spec.loader is not None, f"cannot load {GUARDIAN_PATH}"
guardian = importlib.util.module_from_spec(_spec)
sys.modules["bootmux_network_guardian"] = guardian  # dataclasses needs the module in sys.modules
_spec.loader.exec_module(guardian)

FakeHost = guardian.FakeHost
StateStore = guardian.StateStore
Guardian = guardian.Guardian
prove_identity = guardian.prove_identity
host_is_clean = guardian.host_is_clean
capture_baseline = guardian.capture_baseline
build_repair_plan = guardian.build_repair_plan
build_wifi_toggle_plan = guardian.build_wifi_toggle_plan
execute_plan = guardian.execute_plan
verify = guardian.verify
classify = guardian.classify
repair_once = guardian.repair_once
redact_baseline = guardian.redact_baseline
uninstall_guardian = guardian.uninstall_guardian

BOOTMUX_PEER = guardian.BOOTMUX_PEER
BOOTMUX_USB_VID = guardian.BOOTMUX_USB_VID
BOOTMUX_USB_PID = guardian.BOOTMUX_USB_PID
BOOTMUX_PRODUCT = guardian.BOOTMUX_PRODUCT
BOOTMUX_SERIAL = guardian.BOOTMUX_SERIAL


# --------------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------------- #


def bootmux_usb():
    return [{"vid": BOOTMUX_USB_VID, "pid": BOOTMUX_USB_PID, "product": BOOTMUX_PRODUCT, "serial": BOOTMUX_SERIAL}]


def bootmux_interface(name="en7", address="10.77.0.2"):
    return {"name": name, "addresses": [{"address": address, "netmask": "255.255.255.0"}], "status": "active"}


def unrelated_interfaces():
    return [
        {"name": "en0", "addresses": [{"address": "192.168.1.50", "netmask": "255.255.255.0"}], "status": "active"},
        {"name": "en5", "addresses": [{"address": "172.16.0.5", "netmask": "255.255.255.0"}], "status": "active"},
    ]


def wifi_service():
    return {"order": 1, "name": "Wi-Fi", "device": "en0", "enabled": True}


def ethernet_service():
    return {"order": 2, "name": "Ethernet", "device": "en5", "enabled": True}


def vpn_service():
    return {"order": 3, "name": "CorpVPN", "device": "utun2", "enabled": True}


def tailscale_service():
    return {"order": 4, "name": "Tailscale", "device": "utun3", "enabled": True}


def bootmux_service(name="BOOTMUX USB Ethernet", device="en7"):
    return {"order": 5, "name": name, "device": device, "enabled": True}


def bootmux_default_route(iface="en7"):
    return {"destination": "default", "gateway": BOOTMUX_PEER, "flags": "UGS", "interface": iface}


def wifi_default_route():
    return {"destination": "default", "gateway": "192.168.1.1", "flags": "UGS", "interface": "en0"}


def dhcp_wifi_ipv4():
    return {"mode": "dhcp", "address": "192.168.1.50", "subnet_mask": "255.255.255.0", "router": "192.168.1.1"}


def manual_wifi_ipv4():
    return {"mode": "manual", "address": "192.168.1.99", "subnet_mask": "255.255.255.0", "router": "192.168.1.1"}


def make_store():
    tmp = tempfile.mkdtemp(prefix="bootmux-test-")
    return StateStore(tmp, enforce_owner=False), tmp


def argvs(host):
    return [list(c) for c in host.commands]


def targets_interfaces(host):
    out = set()
    for c in host.commands:
        if len(c) >= 2 and c[1] in ("en0", "en5", "en7", "en8"):
            pass
    return out


def commands_touching(host, token):
    return [c for c in host.commands if token in c]


def assert_no_unrelated_service_commands(testcase, host, bootmux_service_name):
    """No command may disable/enable/reorder an unrelated service."""
    for c in host.commands:
        if "-setnetworkserviceenabled" in c:
            idx = c.index("-setnetworkserviceenabled")
            name = c[idx + 1]
            testcase.assertNotEqual(
                name, "Ethernet", f"unrelated Ethernet service touched: {c}"
            )
            testcase.assertNotEqual(name, "CorpVPN", f"VPN service touched: {c}")
            testcase.assertNotEqual(name, "Tailscale", f"Tailscale service touched: {c}")
        if "-setairportpower" in c or "-setairportnetwork" in c:
            # Wi-Fi toggle is allowed only as R6 last resort; individual tests
            # assert its presence/absence explicitly.
            pass


# --------------------------------------------------------------------------- #
# T01-T03 — identity and no-op behaviour
# --------------------------------------------------------------------------- #


class TestIdentityAndNoOp(unittest.TestCase):
    def test_T01_safe_hid_only_attachment_is_noop(self):
        # BOOTMUX USB present but NO network interface in 10.77.0.0/24.
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces(),
            routes=[wifi_default_route()],
            services=[wifi_service(), ethernet_service()],
            wifi_device="en0",
            wifi_power=True,
            wifi_ipv4=dhcp_wifi_ipv4(),
        )
        identity = prove_identity(host)
        self.assertFalse(identity.proven)
        self.assertFalse(identity.ambiguous)
        self.assertIsNone(identity.interface)
        # Hardware signals present but no network surface -> not a mutation target.
        self.assertTrue(identity.hardware_signals)

        store, tmp = make_store()
        try:
            report = repair_once(host, store)
            self.assertEqual(host.commands, [], "HID-only attachment must be a complete no-op")
            self.assertEqual(report["classification"], "REPAIRED")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T02_no_bootmux_noop_and_baseline_after_stability(self):
        host = FakeHost(
            usb=[],
            interfaces=unrelated_interfaces(),
            routes=[wifi_default_route()],
            services=[wifi_service(), ethernet_service()],
            wifi_device="en0",
            wifi_power=True,
            wifi_ssid="HomeNet",
            wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": ["1.1.1.1"], "search": ["local"]}},
        )
        store, tmp = make_store()
        try:
            g = Guardian(host, store, stability_seconds=15.0)
            first = g.tick()
            self.assertEqual(first["action"], "monitoring_idle")
            self.assertIsNone(store.read_baseline())
            # Not stable yet.
            host.advance(10.0)
            self.assertEqual(g.tick()["action"], "monitoring_idle")
            self.assertIsNone(store.read_baseline())
            # Stable for >= 15s -> baseline captured.
            host.advance(6.0)
            report = g.tick()
            self.assertEqual(report["action"], "baseline_captured")
            baseline = store.read_baseline()
            self.assertIsNotNone(baseline)
            self.assertEqual(baseline["wifi"]["ipv4_mode"], "dhcp")
            self.assertEqual(baseline["wifi"]["associated_ssid"], "HomeNet")
            self.assertEqual(host.commands, [], "baseline capture must not mutate")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T03_ambiguous_1077_interface_audit_only(self):
        # 10.77 interface present but NO hardware signal -> ambiguous, no mutation.
        host = FakeHost(
            usb=[],  # no BOOTMUX USB device
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route(), wifi_default_route()],
            services=[wifi_service(), bootmux_service()],
            wifi_device="en0",
            wifi_power=True,
            wifi_ipv4=dhcp_wifi_ipv4(),
        )
        identity = prove_identity(host)
        self.assertFalse(identity.proven)
        self.assertTrue(identity.ambiguous)

        store, tmp = make_store()
        try:
            report = repair_once(host, store)
            self.assertEqual(report["action"], "audit_only")
            self.assertEqual(report["classification"], "AMBIGUOUS")
            self.assertEqual(host.commands, [], "ambiguous identity must not mutate")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# T04-T05 — route removal precision
# --------------------------------------------------------------------------- #


class TestRouteRemoval(unittest.TestCase):
    def _proven_host(self, extra_routes):
        return FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=extra_routes + [wifi_default_route()],
            services=[wifi_service(), ethernet_service(), bootmux_service()],
            wifi_device="en0",
            wifi_power=True,
            wifi_ipv4=dhcp_wifi_ipv4(),
        )

    def test_T04_proven_default_route_remove_only_that_route(self):
        host = self._proven_host([bootmux_default_route()])
        identity = prove_identity(host)
        self.assertTrue(identity.proven)

        plan = build_repair_plan(host, identity, baseline=None)
        route_cmds = [c for c in plan.commands if c.step == "R1"]
        self.assertEqual(len(route_cmds), 1)
        self.assertEqual(list(route_cmds[0].argv), ["route", "-n", "delete", "default", BOOTMUX_PEER])

        execute_plan(host, plan)
        # Only the BOOTMUX default route removed; Wi-Fi default route intact.
        remaining = [r["gateway"] for r in host.routes() if r["destination"] == "default"]
        self.assertNotIn(BOOTMUX_PEER, remaining)
        self.assertIn("192.168.1.1", remaining)

    def test_T05_proven_scoped_routes_remove_all_and_only_bootmux(self):
        scoped = [
            bootmux_default_route(),
            {"destination": "10.77.0.0/24", "gateway": "link#7", "flags": "U", "interface": "en7"},
            {"destination": "192.168.11.1", "gateway": BOOTMUX_PEER, "flags": "UGHS", "interface": "en7"},
            {"destination": "172.16.0.0/16", "gateway": "172.16.0.1", "flags": "UGS", "interface": "en5"},
        ]
        host = self._proven_host(scoped)
        identity = prove_identity(host)
        self.assertTrue(identity.proven)

        plan = build_repair_plan(host, identity, baseline=None)
        execute_plan(host, plan)

        remaining_gateways = {r["gateway"] for r in host.routes()}
        remaining_dests = {r["destination"] for r in host.routes()}
        # All BOOTMUX routes gone.
        self.assertNotIn(BOOTMUX_PEER, remaining_gateways)
        self.assertNotIn("10.77.0.0/24", remaining_dests)
        self.assertNotIn("192.168.11.1", remaining_dests)
        # Unrelated route untouched.
        self.assertIn("172.16.0.0/16", remaining_dests)
        self.assertIn("172.16.0.1", remaining_gateways)
        # No command targeted the unrelated en5 interface.
        self.assertEqual(commands_touching(host, "en5"), [])


# --------------------------------------------------------------------------- #
# T06-T09 — Wi-Fi IPv4 / DNS restore
# --------------------------------------------------------------------------- #


def baseline_from(host):
    return capture_baseline(host)


class TestWifiRestore(unittest.TestCase):
    def _contaminated_host(self, wifi_ipv4, dns, ssid="HomeNet"):
        return FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route()],
            services=[wifi_service(), ethernet_service(), bootmux_service()],
            wifi_device="en0",
            wifi_power=True,
            wifi_ssid=ssid,
            wifi_ipv4=wifi_ipv4,
            dns=dns,
        )

    def test_T06_detach_dhcp_baseline_restores_dhcp(self):
        # Baseline captured while clean (DHCP).
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service(), ethernet_service()], wifi_device="en0",
            wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        baseline = baseline_from(clean)
        self.assertEqual(baseline["wifi"]["ipv4_mode"], "dhcp")

        # Now contaminated: Wi-Fi lost its DHCP lease (manual/none) + BOOTMUX route.
        host = self._contaminated_host(
            {"mode": "manual", "address": None, "subnet_mask": None, "router": None},
            {"Wi-Fi": {"servers": [], "search": []}},
        )
        identity = prove_identity(host)
        plan = build_repair_plan(host, identity, baseline)
        execute_plan(host, plan)

        dhcp_cmds = commands_touching(host, "DHCP")
        self.assertEqual(len(dhcp_cmds), 1)
        self.assertEqual(dhcp_cmds[0], ["ipconfig", "set", "en0", "DHCP"])
        self.assertEqual(host.wifi_ipv4("en0")["mode"], "dhcp")

    def test_T07_detach_manual_baseline_restores_exact_values(self):
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service(), ethernet_service()], wifi_device="en0",
            wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=manual_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        baseline = baseline_from(clean)
        self.assertEqual(baseline["wifi"]["ipv4_mode"], "manual")

        # Contaminated: DHCP now, must be restored to EXACT manual values.
        host = self._contaminated_host(dhcp_wifi_ipv4(), {"Wi-Fi": {"servers": [], "search": []}})
        identity = prove_identity(host)
        plan = build_repair_plan(host, identity, baseline)
        execute_plan(host, plan)

        manual_cmds = commands_touching(host, "-setmanual")
        self.assertEqual(len(manual_cmds), 1)
        self.assertEqual(
            manual_cmds[0],
            ["networksetup", "-setmanual", "Wi-Fi", "192.168.1.99", "255.255.255.0", "192.168.1.1"],
        )
        # No DHCP conversion of a manual baseline.
        self.assertEqual(commands_touching(host, "DHCP"), [])
        self.assertEqual(host.wifi_ipv4("en0")["mode"], "manual")
        self.assertEqual(host.wifi_ipv4("en0")["address"], "192.168.1.99")

    def test_T08_explicit_dns_baseline_restored(self):
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service()], wifi_device="en0", wifi_power=True,
            wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": ["9.9.9.9", "149.112.112.112"], "search": ["corp.example"]}},
        )
        baseline = baseline_from(clean)

        host = self._contaminated_host(
            dhcp_wifi_ipv4(),
            {"Wi-Fi": {"servers": [BOOTMUX_PEER], "search": []}},
        )
        identity = prove_identity(host)
        plan = build_repair_plan(host, identity, baseline)
        execute_plan(host, plan)

        dns_cmds = commands_touching(host, "-setdnsservers")
        self.assertEqual(len(dns_cmds), 1)
        self.assertEqual(
            dns_cmds[0],
            ["networksetup", "-setdnsservers", "Wi-Fi", "9.9.9.9", "149.112.112.112"],
        )
        search_cmds = commands_touching(host, "-setsearchdomains")
        self.assertEqual(search_cmds[0], ["networksetup", "-setsearchdomains", "Wi-Fi", "corp.example"])
        self.assertEqual(host.dns("Wi-Fi")["servers"], ["9.9.9.9", "149.112.112.112"])

    def test_T09_automatic_dns_baseline_clears_bootmux_dns(self):
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service()], wifi_device="en0", wifi_power=True,
            wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},  # automatic/empty
        )
        baseline = baseline_from(clean)

        host = self._contaminated_host(
            dhcp_wifi_ipv4(),
            {"Wi-Fi": {"servers": [BOOTMUX_PEER], "search": ["bootmux.local"]}},
        )
        identity = prove_identity(host)
        plan = build_repair_plan(host, identity, baseline)
        execute_plan(host, plan)

        dns_cmds = commands_touching(host, "-setdnsservers")
        self.assertEqual(dns_cmds[0], ["networksetup", "-setdnsservers", "Wi-Fi", "Empty"])
        search_cmds = commands_touching(host, "-setsearchdomains")
        self.assertEqual(search_cmds[0], ["networksetup", "-setsearchdomains", "Wi-Fi", "Empty"])
        self.assertEqual(host.dns("Wi-Fi")["servers"], [])
        self.assertEqual(host.dns("Wi-Fi")["search"], [])


# --------------------------------------------------------------------------- #
# T10-T11 — service order / unrelated services
# --------------------------------------------------------------------------- #


class TestServiceOrder(unittest.TestCase):
    def test_T10_contaminated_order_restored_exactly(self):
        clean_services = [wifi_service(), ethernet_service(), vpn_service(), tailscale_service()]
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=clean_services, wifi_device="en0", wifi_power=True,
            wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        baseline = baseline_from(clean)
        self.assertEqual(
            baseline["network"]["network_service_order"],
            ["Wi-Fi", "Ethernet", "CorpVPN", "Tailscale"],
        )

        # Contaminated: BOOTMUX service inserted first, order scrambled.
        scrambled = [
            {"order": 1, "name": "BOOTMUX USB Ethernet", "device": "en7", "enabled": True},
            {"order": 2, "name": "Ethernet", "device": "en5", "enabled": True},
            {"order": 3, "name": "Wi-Fi", "device": "en0", "enabled": True},
            {"order": 4, "name": "CorpVPN", "device": "utun2", "enabled": True},
            {"order": 5, "name": "Tailscale", "device": "utun3", "enabled": True},
        ]
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route()],
            services=scrambled,
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        identity = prove_identity(host)
        plan = build_repair_plan(host, identity, baseline)
        execute_plan(host, plan)

        order_cmds = commands_touching(host, "-ordernetworkservices")
        self.assertEqual(len(order_cmds), 1)
        self.assertEqual(
            order_cmds[0],
            ["networksetup", "-ordernetworkservices", "Wi-Fi", "Ethernet", "CorpVPN", "Tailscale"],
        )
        # R2 disables (never deletes) the BOOTMUX service, so it may remain in the
        # list; R5 guarantees the RELATIVE order of the unrelated services.
        unrelated_order = [n for n in host.service_order() if n != "BOOTMUX USB Ethernet"]
        self.assertEqual(unrelated_order, ["Wi-Fi", "Ethernet", "CorpVPN", "Tailscale"])

    def test_T11_unrelated_ethernet_vpn_tailscale_unchanged(self):
        clean_services = [wifi_service(), ethernet_service(), vpn_service(), tailscale_service()]
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=clean_services, wifi_device="en0", wifi_power=True,
            wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        baseline = baseline_from(clean)

        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route()],
            services=[wifi_service(), ethernet_service(), vpn_service(), tailscale_service(), bootmux_service()],
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        identity = prove_identity(host)
        plan = build_repair_plan(host, identity, baseline)
        execute_plan(host, plan)

        # Only the BOOTMUX service may be disabled.
        enable_cmds = commands_touching(host, "-setnetworkserviceenabled")
        self.assertEqual(len(enable_cmds), 1)
        self.assertEqual(enable_cmds[0], ["networksetup", "-setnetworkserviceenabled", "BOOTMUX USB Ethernet", "off"])
        assert_no_unrelated_service_commands(self, host, "BOOTMUX USB Ethernet")
        # Unrelated services still enabled.
        for svc in host.services():
            if svc["name"] in ("Ethernet", "CorpVPN", "Tailscale"):
                self.assertTrue(svc["enabled"], f"{svc['name']} was disabled")


# --------------------------------------------------------------------------- #
# T12-T14 — Wi-Fi toggle last resort + idempotency
# --------------------------------------------------------------------------- #


class TestWifiToggleAndIdempotency(unittest.TestCase):
    def _baseline(self):
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service()], wifi_device="en0", wifi_power=True,
            wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        return baseline_from(clean)

    def test_T12_repair_succeeds_without_toggle(self):
        baseline = self._baseline()
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route(), wifi_default_route()],
            services=[wifi_service(), bootmux_service()],
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        store, tmp = make_store()
        try:
            store.write_baseline(baseline)
            report = repair_once(host, store)
            self.assertEqual(report["classification"], "REPAIRED")
            self.assertFalse(report["toggled"])
            self.assertEqual(commands_touching(host, "-setairportpower"), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T13_verification_fails_then_one_bounded_toggle(self):
        baseline = self._baseline()
        # Contaminated AND Wi-Fi default route absent so R1-R5 cannot restore
        # the default route -> verification fails -> one bounded toggle.
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route()],  # NO Wi-Fi default route
            services=[wifi_service(), bootmux_service()],
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        store, tmp = make_store()
        try:
            store.write_baseline(baseline)
            report = repair_once(host, store, now=10_000.0)
            self.assertTrue(report["toggled"])
            power_cmds = commands_touching(host, "-setairportpower")
            self.assertEqual(len(power_cmds), 2)
            self.assertEqual(power_cmds[0], ["networksetup", "-setairportpower", "en0", "off"])
            self.assertEqual(power_cmds[1], ["networksetup", "-setairportpower", "en0", "on"])
            rejoin = commands_touching(host, "-setairportnetwork")
            self.assertEqual(rejoin[0], ["networksetup", "-setairportnetwork", "en0", "HomeNet"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T13b_toggle_cooldown_prevents_loop(self):
        baseline = self._baseline()
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route()],
            services=[wifi_service(), bootmux_service()],
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        # Cooldown active (toggled 10s ago) -> no toggle plan.
        plan = build_wifi_toggle_plan(host, baseline, now=1000.0, last_toggle_at=995.0)
        self.assertEqual(plan.commands, [])
        # Cooldown elapsed -> toggle allowed.
        plan2 = build_wifi_toggle_plan(host, baseline, now=1000.0, last_toggle_at=500.0)
        self.assertTrue(plan2.commands)

    def test_T14_repeated_repair_is_idempotent(self):
        baseline = self._baseline()
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route(), wifi_default_route()],
            services=[wifi_service(), bootmux_service()],
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        identity = prove_identity(host)
        plan1 = build_repair_plan(host, identity, baseline)
        first_count = len(plan1.commands)
        self.assertGreater(first_count, 0)
        execute_plan(host, plan1)

        # Second pass over the now-repaired host: no further mutations.
        plan2 = build_repair_plan(host, identity, baseline)
        self.assertEqual(plan2.commands, [], "second repair must be a no-op")


# --------------------------------------------------------------------------- #
# T15-T16 — daemon restart + hardened state store
# --------------------------------------------------------------------------- #


class TestDaemonAndStateStore(unittest.TestCase):
    def test_T15_daemon_restart_with_valid_snapshot_continues(self):
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service()], wifi_device="en0", wifi_power=True,
            wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        store, tmp = make_store()
        try:
            store.write_baseline(baseline_from(clean))

            # New daemon instance (simulating restart) sees a stale BOOTMUX route.
            host = FakeHost(
                usb=[], interfaces=unrelated_interfaces(),
                routes=[bootmux_default_route(), wifi_default_route()],
                services=[wifi_service(), bootmux_service()],
                wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
                dns={"Wi-Fi": {"servers": [], "search": []}},
            )
            g = Guardian(host, store)
            report = g.tick()
            self.assertEqual(report["action"], "repair")
            self.assertEqual(report["reason"], "stale_route")
            self.assertEqual(report["classification"], "REPAIRED")
            # Baseline survived the restart and was used.
            self.assertIsNotNone(store.read_baseline())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T16_corrupt_symlink_wrong_owner_state_fails_closed(self):
        tmp = tempfile.mkdtemp(prefix="bootmux-test-")
        try:
            # Wrong mode on the directory.
            os.chmod(tmp, 0o755)
            store = StateStore(tmp, enforce_owner=False)
            with self.assertRaises(guardian.StateStoreError):
                store.validate_dir()
            os.chmod(tmp, 0o700)

            # Symlinked baseline file -> fail closed.
            real = os.path.join(tmp, "real.json")
            with open(real, "w") as fh:
                fh.write("{}")
            link = os.path.join(tmp, guardian.STATE_BASELINE)
            os.symlink(real, link)
            with self.assertRaises(guardian.StateStoreError):
                store.load(guardian.STATE_BASELINE)
            os.unlink(link)

            # Wrong mode on a baseline file.
            with open(link, "w") as fh:
                fh.write("{}")
            os.chmod(link, 0o644)
            with self.assertRaises(guardian.StateStoreError):
                store.load(guardian.STATE_BASELINE)
            os.chmod(link, 0o600)

            # Schema violation -> fail closed.
            store.atomic_write(guardian.STATE_BASELINE, {"schema_version": 999})
            with self.assertRaises(guardian.StateStoreError):
                store.read_baseline()

            # repair_once on invalid store -> fail_closed, no mutation.
            host = FakeHost(
                usb=bootmux_usb(),
                interfaces=unrelated_interfaces() + [bootmux_interface()],
                routes=[bootmux_default_route()],
                services=[wifi_service(), bootmux_service()],
                wifi_device="en0", wifi_power=True, wifi_ipv4=dhcp_wifi_ipv4(),
            )
            report = repair_once(host, store)
            self.assertEqual(report["action"], "fail_closed")
            self.assertEqual(host.commands, [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# T17-T20 — stale state, no-baseline, failure honesty, uninstall
# --------------------------------------------------------------------------- #


class TestStaleAndUninstall(unittest.TestCase):
    def test_T17_stale_hardware_absent_route_removed_conservatively(self):
        # No USB hardware, no 10.77 interface, but a stale 10.77.0.1 route.
        host = FakeHost(
            usb=[],
            interfaces=unrelated_interfaces(),
            routes=[bootmux_default_route(), wifi_default_route()],
            services=[wifi_service()],
            wifi_device="en0", wifi_power=True, wifi_ipv4=dhcp_wifi_ipv4(),
        )
        identity = prove_identity(host)
        self.assertFalse(identity.proven)
        self.assertFalse(identity.ambiguous)

        store, tmp = make_store()
        try:
            report = repair_once(host, store)
            # Route removed via gateway match even without a proven interface.
            self.assertNotIn(BOOTMUX_PEER, [r["gateway"] for r in host.routes()])
            self.assertIn("192.168.1.1", [r["gateway"] for r in host.routes()])
            self.assertEqual(report["classification"], "REPAIRED")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T18_no_baseline_removes_only_proven_state_invents_nothing(self):
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route(), wifi_default_route()],
            services=[wifi_service(), bootmux_service()],
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet",
            wifi_ipv4={"mode": "manual", "address": "192.168.1.77", "subnet_mask": "255.255.255.0", "router": "192.168.1.1"},
            dns={"Wi-Fi": {"servers": ["8.8.8.8"], "search": []}},
        )
        store, tmp = make_store()
        try:
            self.assertIsNone(store.read_baseline())
            report = repair_once(host, store)
            # BOOTMUX route + service removed.
            self.assertNotIn(BOOTMUX_PEER, [r["gateway"] for r in host.routes()])
            self.assertEqual(commands_touching(host, "-setnetworkserviceenabled")[0][-1], "off")
            # Nothing invented: no manual/dhcp/dns/order commands emitted.
            self.assertEqual(commands_touching(host, "-setmanual"), [])
            self.assertEqual(commands_touching(host, "DHCP"), [])
            self.assertEqual(commands_touching(host, "-setdnsservers"), [])
            self.assertEqual(commands_touching(host, "-ordernetworkservices"), [])
            # Host manual IPv4 untouched.
            self.assertEqual(host.wifi_ipv4("en0")["address"], "192.168.1.77")
            self.assertEqual(host.dns("Wi-Fi")["servers"], ["8.8.8.8"])
            self.assertFalse(report["has_baseline"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T19_command_failure_bounded_honest_classification(self):
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service()], wifi_device="en0", wifi_power=True,
            wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        baseline = baseline_from(clean)
        host = FakeHost(
            usb=bootmux_usb(),
            interfaces=unrelated_interfaces() + [bootmux_interface()],
            routes=[bootmux_default_route(), wifi_default_route()],
            services=[wifi_service(), bootmux_service()],
            wifi_device="en0", wifi_power=True, wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        # Force the route deletion to fail (simulated timeout / non-zero exit).
        host.run_results[("route", "-n", "delete", "default", BOOTMUX_PEER)] = (124, "", "timeout")
        store, tmp = make_store()
        try:
            store.write_baseline(baseline)
            report = repair_once(host, store)
            self.assertNotEqual(report["classification"], "REPAIRED")
            self.assertTrue(report["classification"].startswith("INCOMPLETE"))
            self.assertFalse(report["execution"]["ok"])
            self.assertEqual(report["execution"]["failures"][0]["returncode"], 124)
            # BOOTMUX route still present — honest, not faked green.
            self.assertIn(BOOTMUX_PEER, [r["gateway"] for r in host.routes()])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_T20_uninstall_removes_daemon_state_unrelated_untouched(self):
        store, tmp = make_store()
        try:
            clean = FakeHost(
                usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
                services=[wifi_service()], wifi_device="en0", wifi_power=True,
                wifi_ssid="HomeNet", wifi_ipv4=dhcp_wifi_ipv4(),
                dns={"Wi-Fi": {"servers": [], "search": []}},
            )
            store.write_baseline(baseline_from(clean))
            # Drop an unrelated file that must survive.
            with open(os.path.join(tmp, "unrelated.txt"), "w") as fh:
                fh.write("keep me")

            result = uninstall_guardian(store, purge=False)
            self.assertIn(guardian.STATE_BASELINE, result["preserved_evidence"])
            # Baseline moved to evidence/, not deleted.
            self.assertTrue(os.path.exists(os.path.join(tmp, "evidence", guardian.STATE_BASELINE)))
            self.assertFalse(os.path.exists(os.path.join(tmp, guardian.STATE_BASELINE)))
            # Unrelated file untouched.
            self.assertTrue(os.path.exists(os.path.join(tmp, "unrelated.txt")))

            # Purge variant removes guardian files outright.
            store.write_baseline(baseline_from(clean))
            result2 = uninstall_guardian(store, purge=True)
            self.assertIn(guardian.STATE_BASELINE, result2["removed"])
            self.assertFalse(os.path.exists(os.path.join(tmp, guardian.STATE_BASELINE)))
            self.assertTrue(os.path.exists(os.path.join(tmp, "unrelated.txt")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Redaction guard — SSID must never leak into status/log output.
# --------------------------------------------------------------------------- #


class TestRedaction(unittest.TestCase):
    def test_ssid_redacted_from_status_output(self):
        clean = FakeHost(
            usb=[], interfaces=unrelated_interfaces(), routes=[wifi_default_route()],
            services=[wifi_service()], wifi_device="en0", wifi_power=True,
            wifi_ssid="SuperSecretHome", wifi_ipv4=dhcp_wifi_ipv4(),
            dns={"Wi-Fi": {"servers": [], "search": []}},
        )
        baseline = baseline_from(clean)
        self.assertEqual(baseline["wifi"]["associated_ssid"], "SuperSecretHome")
        redacted = redact_baseline(baseline)
        self.assertEqual(redacted["wifi"]["associated_ssid"], "<redacted>")
        self.assertNotIn("SuperSecretHome", str(redacted))


if __name__ == "__main__":
    unittest.main(verbosity=2)
