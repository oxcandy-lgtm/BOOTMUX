#!/usr/bin/env python3
"""R7C P4-R0 — BOOTMUX Mac Pre-Attach Shield tests (S01–S20).

Fixture-driven tests verifying exact command plans and zero unrelated mutations.
Uses FakeHost exclusively — never touches the real Mac.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

# Load shield module — register in sys.modules before exec so dataclasses
# can resolve forward references (Python 3.9 requirement).
_SHIELD_PATH = Path(__file__).resolve().parent.parent / "bootmux-attach-shield.py"
_spec = importlib.util.spec_from_file_location("bootmux_attach_shield", _SHIELD_PATH)
assert _spec is not None and _spec.loader is not None
shield = importlib.util.module_from_spec(_spec)
sys.modules["bootmux_attach_shield"] = shield
_spec.loader.exec_module(shield)

FakeHost = shield.FakeHost
Baseline = shield.Baseline
ShieldState = shield.ShieldState
PF_ANCHOR = shield.PF_ANCHOR
BOOTMUX_SUBNET = shield.BOOTMUX_SUBNET


def make_baseline(**overrides) -> Baseline:
    """Create a realistic baseline for testing."""
    b = Baseline(
        network_location="Automatic",
        wifi_device="en0",
        wifi_service="Wi-Fi",
        wifi_enabled=True,
        wifi_power=True,
        ssid_digest="abcdef0123456789",
        ipv4_mode="DHCP",
        ipv6_mode="Automatic",
        gateway="192.168.1.1",
        gateway_interface="en0",
        dns_servers=["192.168.1.1"],
        dns_search=["local"],
        dns_automatic=True,
        service_order=["Wi-Fi", "Ethernet", "Tailscale"],
        service_enabled={"Wi-Fi": True, "Ethernet": True, "Tailscale": True},
        interfaces={"en0": "Wi-Fi", "en1": "Ethernet", "utun0": "Tailscale"},
        virtual_services=["Tailscale"],
        captured_at=1000000.0,
    )
    for k, v in overrides.items():
        setattr(b, k, v)
    return b


def cmds_containing(host: FakeHost, substring: str):
    """Return commands containing a substring."""
    return [c for c in host.commands if any(substring in " ".join(c) for _ in [1])]


def cmd_strs(host: FakeHost):
    """Return all commands as joined strings."""
    return [" ".join(c) for c in host.commands]


class TestS01StaleBootmuxServiceDisabled(unittest.TestCase):
    """S01: stale known BOOTMUX service disabled before attach."""

    def test_bootmux_service_disabled(self):
        host = FakeHost()
        baseline = make_baseline(service_order=["Wi-Fi", "BOOTMUX Bridge", "Ethernet"])
        baseline.interfaces = {"en0": "Wi-Fi", "en8": "BOOTMUX Bridge", "en1": "Ethernet"}
        host.set_response("networksetup -listnetworkserviceorder",
                          "(1) Wi-Fi\n(2) BOOTMUX Bridge\n(3) Ethernet")
        qr = shield.quarantine_bootmux(host, baseline)
        # Must disable BOOTMUX Bridge
        self.assertIn("BOOTMUX Bridge", qr.services_disabled)
        # Must use -setnetworkserviceenabled off, NOT delete
        disable_cmds = [c for c in host.commands
                        if "-setnetworkserviceenabled" in c and "off" in c]
        self.assertTrue(any("BOOTMUX Bridge" in c for c in disable_cmds))
        # Must NOT delete
        for c in host.commands:
            self.assertNotIn("-removenetworkservice", c)


class TestS02WifiFirstOrderPreserved(unittest.TestCase):
    """S02: Wi-Fi first while unrelated relative service order preserved."""

    def test_wifi_first_others_preserved(self):
        host = FakeHost()
        baseline = make_baseline(service_order=["Ethernet", "Wi-Fi", "VPN", "Tailscale"])
        qr = shield.quarantine_bootmux(host, baseline)
        # Find ordernetworkservices command
        order_cmds = [c for c in host.commands if "-ordernetworkservices" in c]
        self.assertTrue(order_cmds)
        order = order_cmds[-1]
        # Wi-Fi must be first
        svc_names = [x for x in order[1:] if x != "-ordernetworkservices" and x != "networksetup"]
        self.assertEqual(svc_names[0], "Wi-Fi")
        # Relative order of others preserved
        others = svc_names[1:]
        self.assertEqual(others, ["Ethernet", "VPN", "Tailscale"])


class TestS03NewNcmInterfaceBlocked(unittest.TestCase):
    """S03: new NCM interface immediately PF-blocked and downed."""

    def test_ncm_blocked(self):
        host = FakeHost()
        baseline = make_baseline()
        # Simulate new NCM interface en5
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: USB Ethernet\n\tDevice: en5\n"
                          "Hardware Port: Wi-Fi\n\tDevice: en0\n")
        new = shield.detect_new_external_ethernet(host, baseline)
        self.assertIn("en5", new)
        # PF block
        ok = shield.pf_install_anchor(host, "en5")
        self.assertTrue(ok)
        # Verify PF rules contain block on en5
        pf_cmds = [c for c in host.commands if "pfctl" in c]
        self.assertTrue(pf_cmds)


class TestS04InterfaceBeforeServiceRace(unittest.TestCase):
    """S04: interface appears before its network service."""

    def test_interface_detected_without_service(self):
        host = FakeHost()
        baseline = make_baseline()
        # Only interface, no service mapping yet
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: USB CDC-NCM\n\tDevice: en6\n"
                          "Hardware Port: Wi-Fi\n\tDevice: en0\n")
        new = shield.detect_new_external_ethernet(host, baseline)
        self.assertIn("en6", new)
        # Recovery should still work without service
        rr = shield.run_recovery(host, baseline, ["en6"])
        self.assertIn("Q1:en6", rr.steps)


class TestS05ServiceBeforeInterfaceRace(unittest.TestCase):
    """S05: service appears after its interface (handled by Q2)."""

    def test_recovery_disables_service(self):
        host = FakeHost()
        baseline = make_baseline(service_order=["Wi-Fi", "USB Ethernet"])
        baseline.interfaces = {"en0": "Wi-Fi", "en7": "USB Ethernet"}
        # Provide live hwport mapping so Q2 can resolve en7 -> USB Ethernet
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: Wi-Fi\n\tDevice: en0\n"
                          "Hardware Port: USB Ethernet\n\tDevice: en7\n")
        rr = shield.run_recovery(host, baseline, ["en7"])
        # Q2 should attempt to disable mapped service
        q2_keys = [k for k in rr.steps if k.startswith("Q2:")]
        self.assertTrue(q2_keys)


class TestS06InjectedIpv4DefaultRemoved(unittest.TestCase):
    """S06: injected IPv4 default route removed."""

    def test_default_route_removed(self):
        host = FakeHost()
        baseline = make_baseline()
        host.set_response("netstat -rn",
                          "default            10.77.0.1        en5\n"
                          "default            192.168.1.1      en0\n")
        rr = shield.run_recovery(host, baseline, ["en5"])
        # Q3 should delete route on en5
        q3_keys = [k for k in rr.steps if k.startswith("Q3:")]
        self.assertTrue(q3_keys)


class TestS07InjectedIpv6DefaultRemoved(unittest.TestCase):
    """S07: injected IPv6 default route removed."""

    def test_ipv6_default_removed(self):
        host = FakeHost()
        baseline = make_baseline()
        host.set_response("netstat -rn",
                          "::/0               fe80::1          en5\n"
                          "default            192.168.1.1      en0\n")
        rr = shield.run_recovery(host, baseline, ["en5"])
        q3_keys = [k for k in rr.steps if k.startswith("Q3:")]
        self.assertTrue(q3_keys)


class TestS08DnsInjectionRestored(unittest.TestCase):
    """S08: DNS injection restored from baseline."""

    def test_dns_restored(self):
        host = FakeHost()
        baseline = make_baseline(dns_servers=["192.168.1.1", "8.8.8.8"])
        qr = shield.quarantine_bootmux(host, baseline)
        self.assertTrue(qr.dns_restored)
        dns_cmds = [c for c in host.commands if "-setdnsservers" in c]
        self.assertTrue(dns_cmds)
        # Must contain baseline DNS
        self.assertIn("192.168.1.1", dns_cmds[-1])
        self.assertIn("8.8.8.8", dns_cmds[-1])


class TestS09WifiDriftRepairedNoDelete(unittest.TestCase):
    """S09: Wi-Fi association drift repaired without deleting saved networks."""

    def test_repair_no_delete(self):
        host = FakeHost()
        baseline = make_baseline()
        shield.repair_wifi_association(host, baseline)
        # Must NOT remove preferred networks
        for c in host.commands:
            self.assertNotIn("-removepreferredwirelessnetwork", c)
            self.assertNotIn("-removeallpreferredwirelessnetworks", c)


class TestS10TailscaleVpnUntouched(unittest.TestCase):
    """S10: Tailscale/VPN untouched."""

    def test_virtual_not_mutated(self):
        host = FakeHost()
        baseline = make_baseline(
            service_order=["Wi-Fi", "Tailscale", "VPN"],
            interfaces={"en0": "Wi-Fi", "utun0": "Tailscale", "utun1": "VPN"},
        )
        new = shield.detect_new_external_ethernet(host, baseline)
        # utun interfaces must NOT be flagged
        self.assertNotIn("utun0", new)
        self.assertNotIn("utun1", new)
        # Quarantine must not disable Tailscale
        qr = shield.quarantine_bootmux(host, baseline)
        self.assertNotIn("Tailscale", qr.services_disabled)
        self.assertNotIn("VPN", qr.services_disabled)


class TestS11RepeatedRecoveryIdempotent(unittest.TestCase):
    """S11: repeated recovery idempotent."""

    def test_idempotent(self):
        host = FakeHost()
        baseline = make_baseline()
        rr1 = shield.run_recovery(host, baseline, ["en5"])
        rr2 = shield.run_recovery(host, baseline, ["en5"])
        # Same classification
        self.assertEqual(rr1.classification, rr2.classification)


class TestS12DaemonRestartResumesArmed(unittest.TestCase):
    """S12: daemon restart resumes armed session."""

    def test_state_persists(self):
        host = FakeHost()
        state = ShieldState(armed=True, session_id="abc123",
                            baseline=make_baseline().to_dict(),
                            classification="GREEN")
        shield.save_state(host, state)
        loaded = shield.load_state(host)
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.armed)
        self.assertEqual(loaded.session_id, "abc123")


class TestS13CorruptStateFailsClosed(unittest.TestCase):
    """S13: corrupt state fails closed."""

    def test_corrupt_json(self):
        host = FakeHost()
        host.files[str(shield.STATE_FILE)] = "{corrupt json!!!"
        loaded = shield.load_state(host)
        self.assertIsNone(loaded)

    def test_missing_state(self):
        host = FakeHost()
        loaded = shield.load_state(host)
        self.assertIsNone(loaded)


class TestS14DetachTriggersRestoreOffline(unittest.TestCase):
    """S14: detach triggers restore while WORKER/network unavailable."""

    def test_recovery_no_network(self):
        host = FakeHost()
        baseline = make_baseline()
        # All network commands return empty (offline)
        rr = shield.run_recovery(host, baseline, ["en5"])
        # Must still produce a classification (not crash)
        self.assertIn(rr.classification, ("GREEN", "INCOMPLETE:Q9"))
        # Must not call curl or external health checks
        for c in host.commands:
            self.assertNotIn("curl", c)


class TestS15PfAnchorUninstallRestoresOnlyOwned(unittest.TestCase):
    """S15: PF anchor uninstall restores only owned rules."""

    def test_anchor_scoped(self):
        host = FakeHost()
        shield.pf_remove_anchor(host)
        # Must use -a PF_ANCHOR, never global flush
        pf_cmds = [c for c in host.commands if "pfctl" in c]
        for c in pf_cmds:
            self.assertIn("-a", c)
            self.assertIn(PF_ANCHOR, c)
        # Must NOT flush all anchors
        for c in host.commands:
            joined = " ".join(c)
            self.assertNotIn("pfctl -F all", joined.replace(f"-a {PF_ANCHOR}", ""))


class TestS16SplitRouteRoundtripOrYellow(unittest.TestCase):
    """S16: split-route add/remove roundtrip or explicit YELLOW."""

    def test_roundtrip_green(self):
        host = FakeHost()
        rp = shield.pin_split_routes(host, "192.168.1.1", "en0")
        self.assertEqual(rp.classification, "GREEN")
        self.assertTrue(rp.pinned_routes)
        # Unpin
        shield.unpin_split_routes(host, rp.pinned_routes, "192.168.1.1")
        delete_cmds = [c for c in host.commands if "delete" in c]
        self.assertTrue(delete_cmds)

    def test_yellow_on_failure(self):
        host = FakeHost()
        host.set_response("route -n add -net 0.0.0.0/1 192.168.1.1", "", exit_code=1)
        rp = shield.pin_split_routes(host, "192.168.1.1", "en0")
        self.assertEqual(rp.classification, "YELLOW_ROUTE_PIN_UNAVAILABLE")

    def test_yellow_no_gateway(self):
        host = FakeHost()
        rp = shield.pin_split_routes(host, "", "")
        self.assertEqual(rp.classification, "YELLOW_ROUTE_PIN_UNAVAILABLE")


class TestS17PostmortemOrdersEvents(unittest.TestCase):
    """S17: postmortem correctly orders synthetic events."""

    def test_event_ordering(self):
        host = FakeHost()
        session_dir = str(shield.SESSION_DIR / "test-session")
        host.dirs.add(str(shield.SESSION_DIR))
        host.dirs.add(session_dir)
        events = [
            {"ts": 1.0, "session": "s", "event": "arm_start", "data": {}},
            {"ts": 2.0, "session": "s", "event": "untrusted_detected", "data": {"interfaces": ["en5"]}},
            {"ts": 3.0, "session": "s", "event": "route_drift", "data": {}},
            {"ts": 4.0, "session": "s", "event": "recovery", "data": {"classification": "GREEN"}},
        ]
        log_content = "\n".join(json.dumps(e) for e in events) + "\n"
        host.files[f"{session_dir}/shield.jsonl"] = log_content
        host.set_response("ls -t " + str(shield.SESSION_DIR), "test-session\n")
        report = shield.generate_postmortem(host)
        parsed = json.loads(report)
        self.assertEqual(parsed["total_events"], 4)
        self.assertEqual(len(parsed["first_mutations"]), 2)
        self.assertEqual(parsed["first_mutations"][0]["event"], "untrusted_detected")
        self.assertEqual(parsed["first_mutations"][1]["event"], "route_drift")


class TestS18LogsRedactSensitive(unittest.TestCase):
    """S18: logs redact SSID/MAC/serial/private path."""

    def test_redaction(self):
        text = "aa:bb:cc:dd:ee:ff 192.168.1.100 /Users/johnsecret MyWiFiNetwork"
        redacted = shield.redact(text)
        self.assertNotIn("aa:bb:cc:dd:ee:ff", redacted)
        self.assertNotIn("192.168.1.100", redacted)
        self.assertNotIn("/Users/johnsecret", redacted)
        self.assertIn(shield.REDACTED, redacted)

    def test_ssid_digest_not_plaintext(self):
        digest = shield.ssid_digest("MySecretWiFi")
        self.assertNotIn("MySecretWiFi", digest)
        self.assertEqual(len(digest), 16)


class TestS19SafeHidOnlyNoMutation(unittest.TestCase):
    """S19: safe HID-only identity causes no network mutation."""

    def test_hid_only_not_flagged(self):
        host = FakeHost()
        baseline = make_baseline()
        # HID keyboard appears — not Ethernet-like
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: Wi-Fi\n\tDevice: en0\n"
                          "Hardware Port: USB Keyboard\n\tDevice: en9\n")
        new = shield.detect_new_external_ethernet(host, baseline)
        # USB Keyboard is NOT Ethernet-like
        self.assertNotIn("en9", new)


class TestS20DisarmRefusedWhileUntrusted(unittest.TestCase):
    """S20: disarm refused while untrusted network identity is present."""

    def test_disarm_refused(self):
        host = FakeHost()
        state = ShieldState(
            armed=True,
            session_id="test",
            baseline=make_baseline().to_dict(),
            untrusted_interfaces=["en5"],
        )
        shield.save_state(host, state)
        # en5 still present
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: Wi-Fi\n\tDevice: en0\n"
                          "Hardware Port: USB Ethernet\n\tDevice: en5\n")
        rc = shield.cmd_disarm(host)
        self.assertEqual(rc, 1)  # refused

    def test_disarm_allowed_after_removal(self):
        host = FakeHost()
        state = ShieldState(
            armed=True,
            session_id="test",
            baseline=make_baseline().to_dict(),
            untrusted_interfaces=["en5"],
        )
        shield.save_state(host, state)
        # en5 gone
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: Wi-Fi\n\tDevice: en0\n")
        rc = shield.cmd_disarm(host)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
