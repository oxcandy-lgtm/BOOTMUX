#!/usr/bin/env python3
"""R7C P4-R1 — BOOTMUX Safe Flash Inspector.

Scans firmware binaries for forbidden USB-network strings and verifies
the safe HID-only marker + USB identity.  Fully offline, no network.

Usage:
    python3 bootmux-safe-flash-inspect.py [--manifest PATH] [--build-dir PATH]
    python3 bootmux-safe-flash-inspect.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "firmware" / "esp32s3-router-spike" / "safe-flash-manifest.json"

# ---------------------------------------------------------------------------
# Forbidden / required string tables
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS: List[str] = [
    "CDC_ECM", "CDC_NCM", "RNDIS", "rndis",
    "usb_network", "USB_NETIF", "tinyusb_net", "tusb_net",
    "dhcps_start", "dhcp_server_start",
    "napt_enable", "ip_forward_enable",
    "BOOTMUX Bridge Experimental", "BOOTMUX-R7A-NCM",
    "TUSB_CLASS_CDC", "CDC_COMM_SUBCLASS",
    "lwip_ip_forward", "IP_FORWARD",
]

REQUIRED_MARKERS: List[str] = [
    "BOOTMUX Keyboard Safe",
    "BOOTMUX-HID-SAFE",
]

SAFE_OFF_MARKER = "BOOTMUX_USB_NETWORK_SAFE_OFF"


# ---------------------------------------------------------------------------
# Core inspection
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_binary_strings(data: bytes) -> List[str]:
    """Extract printable ASCII strings >= 6 chars from binary data."""
    return [m.group(0).decode("ascii", errors="replace")
            for m in re.finditer(rb"[\x20-\x7e]{6,}", data)]


def inspect_artifact(path: Path, manifest_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect a single firmware binary against the manifest."""
    result: Dict[str, Any] = {
        "name": manifest_entry["name"],
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        result["status"] = "MISSING"
        return result

    data = path.read_bytes()
    result["size"] = len(data)
    result["expected_size"] = manifest_entry["size"]
    result["size_match"] = len(data) == manifest_entry["size"]

    actual_sha = sha256_file(path)
    result["sha256"] = actual_sha
    result["expected_sha256"] = manifest_entry["sha256"]
    result["sha256_match"] = actual_sha == manifest_entry["sha256"]

    strings = scan_binary_strings(data)
    forbidden_found = [s for s in strings if any(p in s for p in FORBIDDEN_PATTERNS)]
    result["forbidden_found"] = forbidden_found
    result["forbidden_clean"] = len(forbidden_found) == 0

    required_found = [s for s in strings if any(r in s for r in REQUIRED_MARKERS)]
    result["required_found"] = required_found

    result["status"] = "GREEN" if (
        result["size_match"] and result["sha256_match"] and result["forbidden_clean"]
    ) else "RED"
    return result


def inspect_build(build_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Full build inspection: all artifacts + sdkconfig marker + safe-off + USB identity.

    OVERALL=GREEN requires ALL of:
      1. sdkconfig_marker present in sdkconfig
      2. Every artifact: size_match AND sha256_match AND forbidden_clean
      3. SAFE_OFF_MARKER found in application binary
      4. USB identity (product + serial) found in application binary
    """
    results: Dict[str, Any] = {
        "build_dir": str(build_dir),
        "artifacts": [],
        "sdkconfig_marker": False,
        "safe_off_marker": False,
        "usb_identity": {"match": False},
        "overall": "RED",
    }

    # Check sdkconfig for safe marker
    sdkconfig = build_dir.parent / "sdkconfig"
    if sdkconfig.exists():
        content = sdkconfig.read_text(errors="replace")
        marker = manifest.get("sdkconfig_marker", "")
        results["sdkconfig_marker"] = marker in content

    # Inspect each artifact
    all_green = True
    app_data: Optional[bytes] = None
    for entry in manifest.get("artifacts", []):
        art_path = build_dir.parent / entry["path"]
        art_result = inspect_artifact(art_path, entry)
        results["artifacts"].append(art_result)
        if art_result["status"] != "GREEN":
            all_green = False
        if entry["name"] == "application" and art_path.exists():
            app_data = art_path.read_bytes()

    # Check safe-off marker in application binary
    if app_data is not None:
        strings = scan_binary_strings(app_data)
        all_text = "\n".join(strings)
        results["safe_off_marker"] = SAFE_OFF_MARKER in all_text
    else:
        results["safe_off_marker"] = False

    # Check USB identity in application binary
    usb_result = verify_usb_identity(manifest, build_dir)
    results["usb_identity"] = usb_result

    # OVERALL=GREEN only when ALL conditions met
    results["overall"] = "GREEN" if (
        all_green
        and results["sdkconfig_marker"]
        and results["safe_off_marker"]
        and usb_result.get("match", False)
    ) else "RED"
    return results


def verify_usb_identity(manifest: Dict[str, Any], build_dir: Path) -> Dict[str, Any]:
    """Verify USB identity strings in the application binary."""
    usb_id = manifest.get("usb_identity", {})
    result: Dict[str, Any] = {"expected": usb_id, "found": {}, "match": False}

    app_entry = next((a for a in manifest.get("artifacts", []) if a["name"] == "application"), None)
    if not app_entry:
        result["error"] = "no application artifact in manifest"
        return result

    app_path = build_dir.parent / app_entry["path"]
    if not app_path.exists():
        result["error"] = f"application binary not found: {app_path}"
        return result

    data = app_path.read_bytes()
    strings = scan_binary_strings(data)
    all_text = "\n".join(strings)

    for key in ("product", "serial"):
        expected = usb_id.get(key, "")
        result["found"][key] = expected in all_text

    result["match"] = all(result["found"].values())
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_self_test() -> int:
    """Built-in self-test with synthetic data."""
    checks = 0
    failures = 0

    def check(name: str, cond: bool) -> None:
        nonlocal checks, failures
        checks += 1
        if not cond:
            failures += 1
            print(f"  FAIL {name}")
        else:
            print(f"  ok   {name}")

    # T1: forbidden pattern detection
    dirty = b"\x00CDC_ECM\x00RNDIS\x00dhcps_start\x00"
    strings = scan_binary_strings(dirty)
    found = [s for s in strings if any(p in s for p in FORBIDDEN_PATTERNS)]
    check("T1 forbidden detected", len(found) >= 2)

    # T2: clean binary passes
    clean = b"\x00BOOTMUX Keyboard Safe\x00BOOTMUX-HID-SAFE\x00HID report\x00"
    strings2 = scan_binary_strings(clean)
    found2 = [s for s in strings2 if any(p in s for p in FORBIDDEN_PATTERNS)]
    check("T2 clean passes", len(found2) == 0)

    # T3: required markers found
    req = [s for s in strings2 if any(r in s for r in REQUIRED_MARKERS)]
    check("T3 required markers", len(req) >= 2)

    # T4: SHA-256 deterministic
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tf:
        tf.write(b"\x00" * 1024)
        tf_path = Path(tf.name)
    sha1 = sha256_file(tf_path)
    sha2 = sha256_file(tf_path)
    check("T4 sha256 deterministic", sha1 == sha2)
    tf_path.unlink()

    # T5: size mismatch detected
    entry = {"name": "test", "path": "x.bin", "offset": "0x0", "size": 999, "sha256": "abc"}
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tf:
        tf.write(b"\x00" * 100)
        tf_path = Path(tf.name)
    r = inspect_artifact(tf_path, entry)
    check("T5 size mismatch", not r["size_match"])
    tf_path.unlink()

    # T6: missing file handled
    r2 = inspect_artifact(Path("/nonexistent/x.bin"), entry)
    check("T6 missing file", r2["status"] == "MISSING")

    # T7: forbidden patterns list non-empty
    check("T7 forbidden list", len(FORBIDDEN_PATTERNS) >= 10)

    # T8: required markers list non-empty
    check("T8 required list", len(REQUIRED_MARKERS) >= 2)

    print(f"\nSELF_TEST: {checks} checks, {failures} failures")
    print("SELF_TEST=PASS" if failures == 0 else "SELF_TEST=FAIL")
    return 0 if failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="BOOTMUX Safe Flash Inspector")
    parser.add_argument("--manifest", type=str, default=str(DEFAULT_MANIFEST))
    parser.add_argument("--build-dir", type=str, default=None)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"MANIFEST_MISSING: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text())
    build_dir = Path(args.build_dir) if args.build_dir else manifest_path.parent / manifest.get("build_dir", "build-native-r7b-r2")

    result = inspect_build(build_dir, manifest)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"BUILD_DIR: {result['build_dir']}")
        print(f"SDKCONFIG_MARKER: {'GREEN' if result['sdkconfig_marker'] else 'RED'}")
        for art in result["artifacts"]:
            print(f"  {art['name']}: {art['status']}"
                  f" size={'OK' if art.get('size_match') else 'MISMATCH'}"
                  f" sha256={'OK' if art.get('sha256_match') else 'MISMATCH'}"
                  f" forbidden={'CLEAN' if art.get('forbidden_clean') else 'FOUND:' + str(art.get('forbidden_found'))}")
        print(f"SAFE_OFF_MARKER: {'GREEN' if result.get('safe_off_marker') else 'RED'}")
        usb = result.get("usb_identity", {})
        print(f"USB_IDENTITY: {'GREEN' if usb.get('match') else 'RED'}")
        print(f"OVERALL: {result['overall']}")

    return 0 if result["overall"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
