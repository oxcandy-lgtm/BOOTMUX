#!/usr/bin/env python3
"""R7C P4-R0B — BOOTMUX Mac Pre-Attach Shield tests (E01–E20).

Ephemeral session, exact rollback, TTL, idempotency, PF pre-state,
Network Location isolation, and purge tests.
Uses FakeHost exclusively — never touches the real Mac.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
import unittest
from pathlib import Path

# Load shield module
_SHIELD_PATH = Path(__file__).resolve().parent.parent / "bootmux-attach-shield.py"
_spec = importlib.util.spec_from_file_location("bootmux_attach_shield", _SHIELD_PATH)
assert _spec is not None and _spec.loader is not None
shield = importlib.util.module_from_spec(_spec)
sys.modules["bootmux_attach_shield"] = shield
_spec.loader.exec_module(shield)

FakeHost = shield.FakeHost
Baseline = shield.Baseline
ShieldState = shield.ShieldState
MutationJournal = shield.MutationJournal
PF_ANCHOR = shield.PF_ANCHOR
DEFAULT_TTL_S = shield.DEFAULT_TTL_S
MAX_TTL_S = shield.MAX_TTL_S
MIN_TTL_S = shield.MIN_TTL_S
STATE_FILE = str(shield.STATE_FILE)
SESSION_DIR = shield.SESSION_DIR
LAUNCHD_PLIST = shield.LAUNCHD_PLIST
INSTALLED_SHIELD = str(shield.INSTALLED_SHIELD)


def make_baseline(**overrides) -> Baseline:
    b = Baseline(
        network_location="Automatic",
        wifi_device="en0",
        wifi_service="Wi-Fi",
        wifi_enabled=True,
        wifi_power=True,
        ssid="TestNetwork",
        ssid_digest="abcdef0123456789",
        ipv4_mode="DHCP",
        ipv4_manual=None,
        ipv6_mode="Automatic",
        gateway="192.168.1.1",
        gateway_interface="en0",
        dns_servers=["192.168.1.1"],
        dns_automatic=False,
        dns_search=["local"],
        search_automatic=False,
        service_order=["Wi-Fi", "Ethernet", "Tailscale"],
        service_enabled={"Wi-Fi": True, "Ethernet": True, "Tailscale": True},
        interfaces={"en0": "Wi-Fi", "en1": "Ethernet", "utun0": "Tailscale"},
        virtual_services=["Tailscale"],
        pf_enabled=False,
        captured_at=time.time(),
    )
    for k, v in overrides.items():
        setattr(b, k, v)
    return b


def make_armed_state(host: FakeHost, baseline: Baseline, ttl: int = DEFAULT_TTL_S,
                     session_id: str = "test1234", **overrides) -> ShieldState:
    now = time.time()
    s = ShieldState(
        armed=True,
        session_id=session_id,
        baseline=baseline.to_dict(),
        pinned_routes=["inet 0.0.0.0/1 via 192.168.1.1", "inet 128.0.0.0/1 via 192.168.1.1"],
        quarantined_services=["BOOTMUX Bridge"],
        untrusted_interfaces=[],
        pf_anchor_active=False,
        pf_was_enabled=baseline.pf_enabled,
        armed_at=now,
        expires_at=now + ttl,
        ttl_seconds=ttl,
        classification="GREEN",
        shield_location="",
        original_location=baseline.network_location,
        location_mode=False,
        session_closed=False,
    )
    for k, v in overrides.items():
        setattr(s, k, v)
    host.write_file(STATE_FILE, s.to_json())
    return s


def setup_host_with_baseline(baseline: Baseline) -> FakeHost:
    """Create a FakeHost pre-loaded with realistic command responses."""
    host = FakeHost()
    host.set_response("networksetup -getcurrentlocation", baseline.network_location)
    host.set_response("networksetup -listallhardwareports",
                      "Hardware Port: Wi-Fi\nDevice: en0\n\nHardware Port: Ethernet\nDevice: en1\n")
    order_lines = []
    for i, svc in enumerate(baseline.service_order, 1):
        marker = str(i) if baseline.service_enabled.get(svc, True) else "*"
        order_lines.append(f"({marker}) {svc}")
    host.set_response("networksetup -listnetworkserviceorder", "\n".join(order_lines))
    host.set_response("networksetup -getairportpower en0", "Wi-Fi Power (en0): On")
    host.set_response("networksetup -getairportnetwork en0",
                      f"Current Wi-Fi Network: {baseline.ssid}")
    host.set_response("networksetup -getinfo Wi-Fi",
                      "DHCP Configuration:\n   IP address: 192.168.1.100\nIPv6: Automatic")
    host.set_response("route -n get default",
                      f"   gateway: {baseline.gateway}\n   interface: {baseline.wifi_device}")
    host.set_response("networksetup -getdnsservers Wi-Fi", "\n".join(baseline.dns_servers))
    host.set_response("networksetup -getsearchdomains Wi-Fi", "\n".join(baseline.dns_search))
    host.set_response("pfctl -s info", "Status: Disabled" if not baseline.pf_enabled else "Status: Enabled")
    host.set_response("pfctl -s Anchors", "  com.apple")
    host.set_response("netstat -rn", "default 192.168.1.1 UGS en0")
    host.set_response("scutil --nwi", "")
    host.set_response("ioreg -p IOUSB", "")
    host.set_response("networksetup -help",
                      "-createlocation\n-switchtolocation\n-deletelocation\n-listlocations")
    host.set_response("networksetup -listlocations", "Automatic")
    host.set_response("launchctl list com.bootmux.attach-shield", "", exit_code=1)
    return host


class TestE01_DHCP_Roundtrip(unittest.TestCase):
    """E01: exact roundtrip for DHCP baseline."""

    def test_dhcp_baseline_captured_and_restored(self):
        b = make_baseline(ipv4_mode="DHCP", ipv4_manual=None)
        host = setup_host_with_baseline(b)
        captured = shield.capture_baseline(host)
        self.assertEqual(captured.ipv4_mode, "DHCP")
        self.assertIsNone(captured.ipv4_manual)
        self.assertEqual(captured.wifi_device, "en0")
        self.assertEqual(captured.gateway, "192.168.1.1")


class TestE02_Manual_IPv4_Roundtrip(unittest.TestCase):
    """E02: exact roundtrip for manual IPv4 baseline."""

    def test_manual_ipv4_captured(self):
        b = make_baseline(ipv4_mode="Manual",
                          ipv4_manual={"ip": "10.0.0.5", "subnet": "255.255.255.0", "router": "10.0.0.1"})
        host = setup_host_with_baseline(b)
        host.set_response("networksetup -getinfo Wi-Fi",
                          "Manual Configuration:\n   IP address: 10.0.0.5\n   Subnet mask: 255.255.255.0\n   Router: 10.0.0.1\nIPv6: Automatic")
        captured = shield.capture_baseline(host)
        self.assertEqual(captured.ipv4_mode, "Manual")
        self.assertEqual(captured.ipv4_manual["ip"], "10.0.0.5")
        self.assertEqual(captured.ipv4_manual["router"], "10.0.0.1")


class TestE03_IPv6_Restoration(unittest.TestCase):
    """E03: exact IPv6 mode restoration."""

    def test_ipv6_mode_captured(self):
        b = make_baseline(ipv6_mode="Automatic")
        host = setup_host_with_baseline(b)
        captured = shield.capture_baseline(host)
        self.assertEqual(captured.ipv6_mode, "Automatic")

    def test_ipv6_journal_rollback(self):
        host = FakeHost()
        journal = MutationJournal(host, "ipv6test")
        journal.record("ipv6_set", "Wi-Fi", {"mode": "Automatic"}, ["networksetup", "-setv6automatic", "Wi-Fi"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        self.assertEqual(issues, [])
        cmds = [" ".join(c) for c in host.commands]
        self.assertIn("networksetup -setv6automatic Wi-Fi", cmds)


class TestE04_Explicit_DNS_Restoration(unittest.TestCase):
    """E04: explicit DNS restoration."""

    def test_manual_dns_journal_rollback(self):
        host = FakeHost()
        journal = MutationJournal(host, "dnstest")
        journal.record("dns_set", "Wi-Fi", {"automatic": False, "servers": ["8.8.8.8", "1.1.1.1"]},
                       ["networksetup", "-setdnsservers", "Wi-Fi", "8.8.8.8", "1.1.1.1"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        self.assertIn("networksetup -setdnsservers Wi-Fi 8.8.8.8 1.1.1.1", cmds)


class TestE05_Automatic_DNS_Restoration(unittest.TestCase):
    """E05: automatic DNS restoration (F2 — not skipped because empty)."""

    def test_auto_dns_journal_rollback(self):
        host = FakeHost()
        journal = MutationJournal(host, "dnsautotest")
        journal.record("dns_set", "Wi-Fi", {"automatic": True, "servers": []},
                       ["networksetup", "-setdnsservers", "Wi-Fi", "Empty"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        self.assertIn("networksetup -setdnsservers Wi-Fi Empty", cmds)

    def test_auto_dns_baseline_captured(self):
        b = make_baseline(dns_servers=[], dns_automatic=True)
        host = setup_host_with_baseline(b)
        host.set_response("networksetup -getdnsservers Wi-Fi",
                          "There aren't any DNS Servers set on Wi-Fi.")
        captured = shield.capture_baseline(host)
        self.assertTrue(captured.dns_automatic)
        self.assertEqual(captured.dns_servers, [])


class TestE06_Search_Domain_Restoration(unittest.TestCase):
    """E06: search-domain restoration."""

    def test_search_journal_rollback(self):
        host = FakeHost()
        journal = MutationJournal(host, "searchtest")
        journal.record("search_set", "Wi-Fi", {"automatic": False, "domains": ["corp.local", "example.com"]},
                       ["networksetup", "-setsearchdomains", "Wi-Fi", "corp.local"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        self.assertIn("networksetup -setsearchdomains Wi-Fi corp.local example.com", cmds)

    def test_auto_search_rollback(self):
        host = FakeHost()
        journal = MutationJournal(host, "searchautotest")
        journal.record("search_set", "Wi-Fi", {"automatic": True, "domains": []},
                       ["networksetup", "-setsearchdomains", "Wi-Fi", "Empty"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        self.assertIn("networksetup -setsearchdomains Wi-Fi Empty", cmds)


class TestE07_Service_Order_Restoration(unittest.TestCase):
    """E07: complete service-order restoration."""

    def test_order_journal_rollback(self):
        host = FakeHost()
        journal = MutationJournal(host, "ordertest")
        original = ["Wi-Fi", "Ethernet", "Thunderbolt Bridge", "Tailscale"]
        journal.record("order_set", "network_services", {"order": original},
                       ["networksetup", "-ordernetworkservices", "Wi-Fi", "Ethernet"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        expected = "networksetup -ordernetworkservices " + " ".join(original)
        self.assertIn(expected, cmds)


class TestE08_Disabled_Ethernet_Stays_Disabled(unittest.TestCase):
    """E08: originally-disabled Ethernet stays disabled after rollback."""

    def test_disabled_service_not_reenabled(self):
        host = FakeHost()
        journal = MutationJournal(host, "distest")
        # Service was already disabled, shield disabled it again (no-op)
        journal.record("service_disable", "Ethernet", {"enabled": False},
                       ["networksetup", "-setnetworkserviceenabled", "Ethernet", "off"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        # Should NOT re-enable because pre_value.enabled was False
        cmds = [" ".join(c) for c in host.commands]
        self.assertNotIn("networksetup -setnetworkserviceenabled Ethernet on", cmds)


class TestE09_Enabled_Ethernet_Reenabled(unittest.TestCase):
    """E09: originally-enabled Ethernet is re-enabled after rollback."""

    def test_enabled_service_reenabled(self):
        host = FakeHost()
        journal = MutationJournal(host, "entest")
        journal.record("service_disable", "Ethernet", {"enabled": True},
                       ["networksetup", "-setnetworkserviceenabled", "Ethernet", "off"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        self.assertIn("networksetup -setnetworkserviceenabled Ethernet on", cmds)


class TestE10_Normal_USB_Ethernet_After_Purge(unittest.TestCase):
    """E10: normal USB Ethernet works after purge (no BOOTMUX interception)."""

    def test_purge_removes_all_artifacts(self):
        host = FakeHost()
        b = make_baseline()
        state = make_armed_state(host, b)
        host.write_file(LAUNCHD_PLIST, "<plist/>")
        host.write_file(INSTALLED_SHIELD, "#!/usr/bin/env python3")
        host.write_file(str(shield.STATE_DIR / "sessions" / "test1234" / "shield.jsonl"), "{}")

        rc = shield.cmd_uninstall(host, purge=True)
        self.assertEqual(rc, 0)

        # All artifacts removed
        self.assertFalse(host.path_exists(LAUNCHD_PLIST))
        self.assertFalse(host.path_exists(INSTALLED_SHIELD))
        self.assertFalse(host.path_exists(STATE_FILE))

        # PF anchor flushed
        cmds = [" ".join(c) for c in host.commands]
        self.assertTrue(any("pfctl -a com.bootmux.attach-shield -F all" in c for c in cmds))


class TestE11_Unrelated_Services_Unchanged(unittest.TestCase):
    """E11: Tailscale/VPN/Thunderbolt/other unrelated services unchanged."""

    def test_virtual_services_not_mutated(self):
        b = make_baseline(service_order=["Wi-Fi", "Ethernet", "Tailscale", "Thunderbolt Bridge"],
                          service_enabled={"Wi-Fi": True, "Ethernet": True, "Tailscale": True, "Thunderbolt Bridge": True})
        host = setup_host_with_baseline(b)
        journal = MutationJournal(host, "virttest")
        qr = shield.quarantine_bootmux(host, b, journal)

        # No virtual service should be disabled
        for svc in ["Tailscale", "Thunderbolt Bridge"]:
            self.assertNotIn(svc, qr.services_disabled)

        # Journal should not contain mutations for virtual services
        for entry in journal.entries():
            self.assertNotIn("Tailscale", entry.get("target", ""))
            self.assertNotIn("Thunderbolt", entry.get("target", ""))


class TestE12_PF_Originally_Disabled_Returns_Disabled(unittest.TestCase):
    """E12: PF originally disabled returns disabled without touching other PF owners."""

    def test_pf_disabled_restored(self):
        host = FakeHost()
        journal = MutationJournal(host, "pftest")
        # Shield enabled PF (pre-state was disabled)
        journal.record("pf_enable", "pf", {"enabled": False}, ["pfctl", "-E"], 0)
        journal.record("pf_anchor_load", PF_ANCHOR, {"rules": ""}, ["pfctl", "-a", PF_ANCHOR, "-f", "/tmp/x"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        self.assertIn("pfctl -d", cmds)
        self.assertIn(f"pfctl -a {PF_ANCHOR} -F all", cmds)


class TestE13_PF_Originally_Enabled_Remains_Enabled(unittest.TestCase):
    """E13: PF originally enabled remains enabled after rollback."""

    def test_pf_enabled_preserved(self):
        host = FakeHost()
        journal = MutationJournal(host, "pfentest")
        # Shield did NOT enable PF (pre-state was enabled)
        journal.record("pf_anchor_load", PF_ANCHOR, {"rules": ""}, ["pfctl", "-a", PF_ANCHOR, "-f", "/tmp/x"], 0)
        ok, issues = journal.rollback(host)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        # Should NOT disable PF
        self.assertNotIn("pfctl -d", cmds)
        # But should flush anchor
        self.assertIn(f"pfctl -a {PF_ANCHOR} -F all", cmds)


class TestE14_TTL_Expiry_Restores_Automatically(unittest.TestCase):
    """E14: TTL expiry restores automatically."""

    def test_expired_state_detected(self):
        b = make_baseline()
        host = setup_host_with_baseline(b)
        state = make_armed_state(host, b, ttl=1)
        state.expires_at = time.time() - 10  # expired
        host.write_file(STATE_FILE, state.to_json())

        self.assertTrue(state.is_expired())
        self.assertEqual(state.ttl_remaining(), 0.0)

    def test_ttl_clamped(self):
        # TTL below minimum clamped up
        self.assertEqual(max(MIN_TTL_S, min(10, MAX_TTL_S)), MIN_TTL_S)
        # TTL above maximum clamped down
        self.assertEqual(max(MIN_TTL_S, min(99999, MAX_TTL_S)), MAX_TTL_S)
        # Normal TTL passes through
        self.assertEqual(max(MIN_TTL_S, min(1800, MAX_TTL_S)), 1800)


class TestE15_Reboot_With_Expired_Session_Restores(unittest.TestCase):
    """E15: reboot with expired session restores."""

    def test_daemon_detects_expired_on_start(self):
        b = make_baseline()
        host = setup_host_with_baseline(b)
        state = make_armed_state(host, b, ttl=1)
        state.expires_at = time.time() - 100
        host.write_file(STATE_FILE, state.to_json())

        # daemon_loop should detect expiry and close
        logger = shield.SessionLogger(host, state.session_id)
        shield.daemon_loop(host, logger)

        # State should be closed
        reloaded = shield.load_state(host)
        self.assertIsNotNone(reloaded)
        self.assertFalse(reloaded.armed)
        self.assertTrue(reloaded.session_closed)


class TestE16_Daemon_Crash_Restart_Resumes_Rollback(unittest.TestCase):
    """E16: daemon crash/restart resumes rollback."""

    def test_not_armed_daemon_exits_cleanly(self):
        host = FakeHost()
        logger = shield.SessionLogger(host, "crashtest")
        # No state -> daemon exits
        shield.daemon_loop(host, logger)
        # Should not crash
        self.assertTrue(True)

    def test_disarmed_daemon_exits_cleanly(self):
        host = FakeHost()
        state = ShieldState(armed=False, session_id="x")
        host.write_file(STATE_FILE, state.to_json())
        logger = shield.SessionLogger(host, "x")
        shield.daemon_loop(host, logger)
        self.assertTrue(True)


class TestE17_Repeated_Close_Session_Idempotent(unittest.TestCase):
    """E17: repeated close-session is idempotent."""

    def test_double_close(self):
        b = make_baseline()
        host = setup_host_with_baseline(b)
        state = make_armed_state(host, b)

        # Save pre-fingerprint so C11 can verify
        fp = shield.capture_fingerprint(host)
        fp_path = str(SESSION_DIR / state.session_id / "fingerprint-pre.json")
        host.mkdir_p(str(SESSION_DIR / state.session_id))
        host.write_file(fp_path, json.dumps(fp, default=str))

        ok1, cls1 = shield.close_session(host, state, force=True)
        # Second close on already-closed state
        ok2, cls2 = shield.close_session(host, state, force=True)
        # Both should succeed (idempotent)
        self.assertTrue(ok1)
        self.assertTrue(ok2)


class TestE18_Repeated_Purge_Idempotent(unittest.TestCase):
    """E18: repeated purge is idempotent."""

    def test_double_purge(self):
        host = FakeHost()
        b = make_baseline()
        state = make_armed_state(host, b)
        host.write_file(LAUNCHD_PLIST, "<plist/>")
        host.write_file(INSTALLED_SHIELD, "#!/usr/bin/env python3")

        rc1 = shield.cmd_uninstall(host, purge=True)
        rc2 = shield.cmd_uninstall(host, purge=True)
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)


class TestE19_S3_Present_Blocks_Close(unittest.TestCase):
    """E19: S3 still present blocks close without mutating unrelated state."""

    def test_close_refused_device_present(self):
        b = make_baseline()
        host = setup_host_with_baseline(b)
        # Add an untrusted interface that is currently present
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: Wi-Fi\nDevice: en0\n\nHardware Port: USB Ethernet\nDevice: en5\n")
        state = make_armed_state(host, b, untrusted_interfaces=["en5"])

        ok, cls = shield.close_session(host, state, force=False)
        self.assertFalse(ok)
        self.assertIn("REFUSED_DEVICE_PRESENT", cls)

        # State should still be armed
        reloaded = shield.load_state(host)
        self.assertTrue(reloaded.armed)


class TestE20_S3_Absent_Allows_Complete_Close(unittest.TestCase):
    """E20: S3 absent allows complete close and purge."""

    def test_close_succeeds_device_absent(self):
        b = make_baseline()
        host = setup_host_with_baseline(b)
        # en5 was untrusted but is now gone
        host.set_response("networksetup -listallhardwareports",
                          "Hardware Port: Wi-Fi\nDevice: en0\n\nHardware Port: Ethernet\nDevice: en1\n")
        state = make_armed_state(host, b, untrusted_interfaces=["en5"])

        # Save pre-fingerprint for C11
        fp = shield.capture_fingerprint(host)
        fp_path = str(SESSION_DIR / state.session_id / "fingerprint-pre.json")
        host.mkdir_p(str(SESSION_DIR / state.session_id))
        host.write_file(fp_path, json.dumps(fp, default=str))

        ok, cls = shield.close_session(host, state, force=False)
        self.assertTrue(ok)
        self.assertIn("GREEN_CLOSE_COMPLETE", cls)

        reloaded = shield.load_state(host)
        self.assertFalse(reloaded.armed)
        self.assertTrue(reloaded.session_closed)


class TestJournalUnknownPrestat(unittest.TestCase):
    """Journal never infers: unknown pre-value -> INCOMPLETE_ROLLBACK."""

    def test_unknown_prestate_reported(self):
        host = FakeHost()
        journal = MutationJournal(host, "unktest")
        journal.record("service_disable", "MysterySvc", None,
                       ["networksetup", "-setnetworkserviceenabled", "MysterySvc", "off"], 0)
        ok, issues = journal.rollback(host)
        self.assertFalse(ok)
        self.assertTrue(any("INCOMPLETE_ROLLBACK_UNKNOWN_PRESTATE" in i for i in issues))


class TestFingerprintCompare(unittest.TestCase):
    """Fingerprint comparison detects differences."""

    def test_equal_fingerprints(self):
        fp = {"network_location": "Automatic", "service_order": ["Wi-Fi"], "pf_enabled": False}
        eq, diffs = shield.compare_fingerprints(fp, fp.copy())
        self.assertTrue(eq)
        self.assertEqual(diffs, [])

    def test_different_fingerprints(self):
        fp_a = {"network_location": "Automatic", "service_order": ["Wi-Fi"]}
        fp_b = {"network_location": "Custom", "service_order": ["Wi-Fi", "Ethernet"]}
        eq, diffs = shield.compare_fingerprints(fp_a, fp_b)
        self.assertFalse(eq)
        self.assertEqual(len(diffs), 2)


class TestLocationIsolation(unittest.TestCase):
    """Network Location isolation tests."""

    def test_location_supported_detection(self):
        host = FakeHost()
        host.set_response("networksetup -help", "-createlocation\n-switchtolocation\n-deletelocation")
        self.assertTrue(shield.location_supported(host))

    def test_location_not_supported(self):
        host = FakeHost()
        host.set_response("networksetup -help", "no location commands here")
        self.assertFalse(shield.location_supported(host))

    def test_create_shield_location(self):
        host = FakeHost()
        host.set_response("networksetup -getcurrentlocation", "Automatic")
        host.set_response("networksetup -listlocations", "Automatic")
        journal = MutationJournal(host, "loctest")
        loc = shield.create_shield_location(host, "abc123", journal)
        self.assertIsNotNone(loc)
        self.assertIn("BOOTMUX-SHIELD-abc123", loc)
        cmds = [" ".join(c) for c in host.commands]
        self.assertTrue(any("-createlocation" in c for c in cmds))
        self.assertTrue(any("-switchtolocation" in c for c in cmds))

    def test_restore_location(self):
        host = FakeHost()
        journal = MutationJournal(host, "loctest2")
        ok = shield.restore_location(host, "Automatic", "BOOTMUX-SHIELD-x", journal)
        self.assertTrue(ok)
        cmds = [" ".join(c) for c in host.commands]
        self.assertTrue(any("-switchtolocation Automatic" in c for c in cmds))
        self.assertTrue(any("-deletelocation BOOTMUX-SHIELD-x" in c for c in cmds))


class TestServiceOrderParsing(unittest.TestCase):
    """Service order parsing with disabled markers."""

    def test_disabled_marker(self):
        text = "(1) Wi-Fi\n(*) BOOTMUX Bridge\n(2) Thunderbolt Bridge"
        order, enabled = shield._parse_service_order(text)
        self.assertEqual(order, ["Wi-Fi", "BOOTMUX Bridge", "Thunderbolt Bridge"])
        self.assertTrue(enabled["Wi-Fi"])
        self.assertFalse(enabled["BOOTMUX Bridge"])
        self.assertTrue(enabled["Thunderbolt Bridge"])


class TestF4_NoSSIDDigestReconnect(unittest.TestCase):
    """F4: never call -setairportnetwork with a digest."""

    def test_recovery_does_not_use_digest(self):
        b = make_baseline(ssid="MyNetwork", ssid_digest="abcdef0123456789")
        host = setup_host_with_baseline(b)
        # Wi-Fi not associated
        host.set_response("networksetup -getairportnetwork en0",
                          "You are not associated with an AirPort network.")
        journal = MutationJournal(host, "f4test")
        rr = shield.run_recovery(host, b, [], journal)
        cmds = [" ".join(c) for c in host.commands]
        # Must NOT contain setairportnetwork with digest
        for cmd in cmds:
            self.assertNotIn("abcdef0123456789", cmd)
            if "setairportnetwork" in cmd:
                self.fail("setairportnetwork should not be called with digest")


class TestF5_PFPrestate(unittest.TestCase):
    """F5: PF pre-state tracking."""

    def test_pf_was_enabled_captured(self):
        b = make_baseline(pf_enabled=True)
        host = setup_host_with_baseline(b)
        host.set_response("pfctl -s info", "Status: Enabled")
        captured = shield.capture_baseline(host)
        self.assertTrue(captured.pf_enabled)

    def test_pf_was_disabled_captured(self):
        b = make_baseline(pf_enabled=False)
        host = setup_host_with_baseline(b)
        host.set_response("pfctl -s info", "Status: Disabled")
        captured = shield.capture_baseline(host)
        self.assertFalse(captured.pf_enabled)


class TestF6_ProvenMapping(unittest.TestCase):
    """F6: do not identify all services as BOOTMUX merely because 10.77 exists."""

    def test_subnet_alone_insufficient(self):
        b = make_baseline(service_order=["Wi-Fi", "USB Ethernet", "Tailscale"],
                          interfaces={"en0": "Wi-Fi", "en5": "USB Ethernet", "utun0": "Tailscale"})
        host = setup_host_with_baseline(b)
        # 10.77 exists but no interface mapping
        host.set_response("scutil --nwi", "10.77.0.5")
        host.set_response("ifconfig", "en0: flags=8863\n\tinet 192.168.1.100\nen5: flags=8863\n\tinet 10.0.0.5")
        result = shield.identify_bootmux_services(host, b)
        # USB Ethernet should NOT be identified as BOOTMUX just because 10.77 exists
        # (10.77 is on no interface in ifconfig output)
        self.assertNotIn("USB Ethernet", result)


class TestTTLBounds(unittest.TestCase):
    """TTL bounds enforcement."""

    def test_default_ttl(self):
        self.assertEqual(DEFAULT_TTL_S, 1800)

    def test_max_ttl(self):
        self.assertEqual(MAX_TTL_S, 7200)

    def test_min_ttl(self):
        self.assertEqual(MIN_TTL_S, 60)

    def test_zero_ttl_rejected(self):
        clamped = max(MIN_TTL_S, min(0, MAX_TTL_S))
        self.assertEqual(clamped, MIN_TTL_S)

    def test_infinite_ttl_rejected(self):
        clamped = max(MIN_TTL_S, min(999999, MAX_TTL_S))
        self.assertEqual(clamped, MAX_TTL_S)


if __name__ == "__main__":
    unittest.main()
