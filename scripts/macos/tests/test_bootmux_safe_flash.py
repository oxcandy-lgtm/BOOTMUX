#!/usr/bin/env python3
"""R7C P4-R1 — BOOTMUX Safe Flash focused tests.

Tests: inspector, runner serial detection, device rejection,
journal crash recovery, manifest validation, offline bundle integrity.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Load modules by path (Python 3.9 compat)
SCRIPTS_DIR = Path(__file__).resolve().parent.parent

def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None, f"Cannot load {filename}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

inspect_mod = _load("bootmux_safe_flash_inspect", "bootmux-safe-flash-inspect.py")
runner_mod = _load("bootmux_safe_flash_runner", "bootmux-safe-flash-runner.py")


class TestInspector(unittest.TestCase):
    """F01-F08: Inspector tests."""

    def test_F01_forbidden_detected(self):
        data = b"\x00CDC_ECM\x00RNDIS\x00dhcps_start\x00napt_enable\x00"
        strings = inspect_mod.scan_binary_strings(data)
        found = [s for s in strings if any(p in s for p in inspect_mod.FORBIDDEN_PATTERNS)]
        self.assertGreaterEqual(len(found), 3)

    def test_F02_clean_binary(self):
        data = b"\x00BOOTMUX Keyboard Safe\x00HID report\x00keyboard\x00"
        strings = inspect_mod.scan_binary_strings(data)
        found = [s for s in strings if any(p in s for p in inspect_mod.FORBIDDEN_PATTERNS)]
        self.assertEqual(len(found), 0)

    def test_F03_required_markers(self):
        data = b"\x00BOOTMUX Keyboard Safe\x00BOOTMUX-HID-SAFE\x00"
        strings = inspect_mod.scan_binary_strings(data)
        found = [s for s in strings if any(r in s for r in inspect_mod.REQUIRED_MARKERS)]
        self.assertGreaterEqual(len(found), 2)

    def test_F04_sha256_deterministic(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tf:
            tf.write(b"\xAB" * 2048)
            path = Path(tf.name)
        sha1 = inspect_mod.sha256_file(path)
        sha2 = inspect_mod.sha256_file(path)
        self.assertEqual(sha1, sha2)
        path.unlink()

    def test_F05_size_mismatch(self):
        entry = {"name": "test", "path": "x.bin", "offset": "0x0", "size": 999, "sha256": "abc"}
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tf:
            tf.write(b"\x00" * 100)
            path = Path(tf.name)
        r = inspect_mod.inspect_artifact(path, entry)
        self.assertFalse(r["size_match"])
        self.assertEqual(r["status"], "RED")
        path.unlink()

    def test_F06_missing_file(self):
        entry = {"name": "test", "path": "x.bin", "offset": "0x0", "size": 100, "sha256": "abc"}
        r = inspect_mod.inspect_artifact(Path("/nonexistent/x.bin"), entry)
        self.assertEqual(r["status"], "MISSING")

    def test_F07_forbidden_list_comprehensive(self):
        self.assertGreaterEqual(len(inspect_mod.FORBIDDEN_PATTERNS), 10)
        # Must include key patterns
        for p in ["CDC_ECM", "CDC_NCM", "RNDIS", "dhcps_start", "napt_enable", "ip_forward_enable"]:
            self.assertIn(p, inspect_mod.FORBIDDEN_PATTERNS)

    def test_F08_usb_identity_check(self):
        manifest = {
            "usb_identity": {"product": "BOOTMUX Keyboard Safe", "serial": "BOOTMUX-HID-SAFE"},
            "artifacts": [{"name": "application", "path": "app.bin", "offset": "0x10000",
                           "size": 100, "sha256": "abc"}],
        }
        with tempfile.TemporaryDirectory() as td:
            # verify_usb_identity uses build_dir.parent / path
            build_dir = Path(td) / "build"
            build_dir.mkdir()
            app_path = Path(td) / "app.bin"
            app_path.write_bytes(b"\x00BOOTMUX Keyboard Safe\x00BOOTMUX-HID-SAFE\x00" + b"\x00" * 50)
            result = inspect_mod.verify_usb_identity(manifest, build_dir)
            self.assertTrue(result["match"])


class TestSerialDetection(unittest.TestCase):
    """F09-F14: Serial port detection and rejection."""

    def test_F09_single_candidate(self):
        before = ["/dev/cu.usbserial-110"]
        after = ["/dev/cu.usbserial-110", "/dev/cu.usbmodem101"]
        port, reason = runner_mod.detect_new_port(before, after)
        self.assertEqual(port, "/dev/cu.usbmodem101")
        self.assertEqual(reason, "SINGLE_CANDIDATE")

    def test_F10_no_new_port(self):
        before = ["/dev/cu.usbserial-110"]
        after = ["/dev/cu.usbserial-110"]
        port, reason = runner_mod.detect_new_port(before, after)
        self.assertIsNone(port)
        self.assertIn("NO_NEW_PORT", reason)

    def test_F11_ambiguous(self):
        before = []
        after = ["/dev/cu.usbmodem101", "/dev/cu.usbmodem202"]
        port, reason = runner_mod.detect_new_port(before, after)
        self.assertIsNone(port)
        self.assertIn("AMBIGUOUS", reason)

    def test_F12_bluetooth_rejected(self):
        rej, reason = runner_mod.is_rejected_device("/dev/cu.Bluetooth-Incoming-Port")
        self.assertTrue(rej)
        self.assertIn("Bluetooth", reason)

    def test_F13_phone_rejected(self):
        for name in ["iPhone", "Android", "Samsung", "Pixel"]:
            rej, _ = runner_mod.is_rejected_device(f"/dev/cu.{name}-Modem")
            self.assertTrue(rej, f"{name} should be rejected")

    def test_F14_network_interface_rejected(self):
        for name in ["en0", "en8", "bridge0", "BOOTMUX Bridge"]:
            rej, _ = runner_mod.is_rejected_device(f"/dev/{name}")
            self.assertTrue(rej, f"{name} should be rejected")


class TestJournal(unittest.TestCase):
    """F15-F18: Journal crash recovery."""

    def test_F15_append_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            j = runner_mod.FlashJournal("test-session", Path(td))
            j.init()
            j.append("STEP_A", {"x": 1})
            j.append("STEP_B", {"y": 2})
            entries = j.load()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].event, "STEP_A")
            self.assertEqual(entries[1].event, "STEP_B")

    def test_F16_last_event(self):
        with tempfile.TemporaryDirectory() as td:
            j = runner_mod.FlashJournal("test-session", Path(td))
            j.init()
            j.append("INIT")
            j.append("FLASH")
            self.assertEqual(j.last_event(), "FLASH")

    def test_F17_can_resume(self):
        with tempfile.TemporaryDirectory() as td:
            j = runner_mod.FlashJournal("test-session", Path(td))
            j.init()
            j.append("INIT")
            j.append("SHIELD_ARM")
            self.assertTrue(j.can_resume_from("SHIELD_ARM"))
            self.assertFalse(j.can_resume_from("FLASH"))

    def test_F18_fsync_durability(self):
        with tempfile.TemporaryDirectory() as td:
            j = runner_mod.FlashJournal("test-session", Path(td))
            j.init()
            j.append("DURABLE", {"data": "x" * 1000})
            # Re-read from disk
            j2 = runner_mod.FlashJournal("test-session", Path(td))
            entries = j2.load()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].event, "DURABLE")


class TestRunnerStatus(unittest.TestCase):
    """F19-F20: Runner status and dry-run."""

    def test_F19_runner_status(self):
        runner = runner_mod.SafeFlashRunner(session_id="test-status", dry_run=True)
        # Runner should be constructable
        self.assertTrue(runner.dry_run)
        self.assertEqual(runner.session_id, "test-status")

    def test_F20_ttl_constant(self):
        self.assertEqual(runner_mod.TTL_SECONDS, 1800)


class TestManifest(unittest.TestCase):
    """F21-F23: Manifest validation."""

    def test_F21_manifest_exists(self):
        manifest_path = runner_mod.MANIFEST_PATH
        self.assertTrue(manifest_path.exists(), f"Manifest missing: {manifest_path}")

    def test_F22_manifest_structure(self):
        manifest = json.loads(runner_mod.MANIFEST_PATH.read_text())
        self.assertIn("artifacts", manifest)
        self.assertIn("usb_identity", manifest)
        self.assertIn("flash_params", manifest)
        self.assertEqual(len(manifest["artifacts"]), 3)
        for art in manifest["artifacts"]:
            self.assertIn("name", art)
            self.assertIn("offset", art)
            self.assertIn("size", art)
            self.assertIn("sha256", art)

    def test_F23_flash_offsets_pinned(self):
        manifest = json.loads(runner_mod.MANIFEST_PATH.read_text())
        offsets = {a["name"]: a["offset"] for a in manifest["artifacts"]}
        self.assertEqual(offsets["bootloader"], "0x0")
        self.assertEqual(offsets["partition-table"], "0x8000")
        self.assertEqual(offsets["application"], "0x10000")


if __name__ == "__main__":
    unittest.main()
