#!/usr/bin/env python3
"""R7C P4 — USB identity oracle (read-only, sanitized).

Parses `system_profiler SPUSBDataType` and decides whether an attached device
satisfies the safe HID-only contract:

  * product identifies as "BOOTMUX Keyboard Safe"
  * serial identifies as "BOOTMUX-HID-SAFE" (where macOS exposes it)
  * a HID interface/class is present
  * NO NCM / ECM / RNDIS / CDC-Ethernet / "USB Ethernet" class is present

The parser is a pure function over text so it can be proven with fixtures
without any device attached.  The CLI runs system_profiler and prints a
sanitized verdict (no serial numbers, vendor IDs, or location IDs leak).

Commands:
  live      run system_profiler and print the sanitized verdict
  selftest  run built-in fixture checks (no device, no mutation)
"""

import argparse
import json
import re
import subprocess
import sys

SAFE_PRODUCT = "BOOTMUX Keyboard Safe"
SAFE_SERIAL = "BOOTMUX-HID-SAFE"

# Substrings that indicate a USB network class (must be ABSENT for safe profile).
NETWORK_CLASS_MARKERS = [
    "ncm", "ecm", "rndis", "cdc-ethernet", "cdc ethernet",
    "usb ethernet", "ethernet", "network", "eem",
]
# Substrings that indicate HID is present.
HID_MARKERS = ["hid", "keyboard", "human interface"]


def parse_usb_devices(text: str):
    """Parse SPUSBDataType text into a list of device dicts (pure).

    Indentation in system_profiler output is variable, so we classify by shape
    rather than column: a line of the form ``Name:`` (colon, no value) opens a
    new device; a line of the form ``Key: Value`` is a field of the current
    device.  This is robust to the bus/controller nesting levels.
    """
    devices = []
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        # Device header: "Something:" with nothing after the colon.
        header = re.match(r"^(.+?):\s*$", stripped)
        if header:
            if current:
                devices.append(current)
            current = {"name": header.group(1).strip(), "fields": {}}
            continue
        # Field line: "Key: Value".
        field = re.match(r"^(.+?):\s+(.*)$", stripped)
        if field and current is not None:
            current["fields"][field.group(1).strip()] = field.group(2).strip()
    if current:
        devices.append(current)
    return devices


def classify_bootmux(devices):
    """Return a sanitized verdict dict for any BOOTMUX device present (pure)."""
    bootmux = [d for d in devices if "bootmux" in d["name"].lower()
               or "bootmux" in str(d["fields"].get("Product ID", "")).lower()
               or SAFE_PRODUCT.lower() in str(d["fields"].get("Product", "")).lower()
               or SAFE_PRODUCT.lower() in d["name"].lower()]

    if not bootmux:
        return {
            "bootmux_device_present": False,
            "product_is_safe": None,
            "serial_is_safe": None,
            "hid_present": None,
            "network_class_absent": None,
            "verdict": "NO_BOOTMUX_DEVICE",
        }

    dev = bootmux[0]
    fields = dev["fields"]
    product = fields.get("Product", dev["name"])
    serial = fields.get("Serial Number", "")
    # Concatenate all field text to scan for class markers.
    blob = " ".join(f"{k} {v}" for k, v in fields.items()).lower()
    blob += " " + dev["name"].lower()

    product_is_safe = product.strip() == SAFE_PRODUCT
    serial_is_safe = (serial.strip() == SAFE_SERIAL) if serial else None
    hid_present = any(m in blob for m in HID_MARKERS)
    network_markers_found = [m for m in NETWORK_CLASS_MARKERS if m in blob]
    network_class_absent = len(network_markers_found) == 0

    if product_is_safe and hid_present and network_class_absent:
        verdict = "SAFE_HID_ONLY"
    elif network_markers_found:
        verdict = "NETWORK_CLASS_PRESENT"
    elif not product_is_safe:
        verdict = "UNSAFE_PRODUCT"
    else:
        verdict = "AMBIGUOUS"

    return {
        "bootmux_device_present": True,
        "product_is_safe": product_is_safe,
        "serial_is_safe": serial_is_safe,
        "hid_present": hid_present,
        "network_class_absent": network_class_absent,
        "network_markers_found": network_markers_found,
        "verdict": verdict,
        # sanitized: no serial number, vendor/product ID, or location ID emitted
    }


# --------------------------------------------------------------------------- #
# Fixtures for self-test (no device required)
# --------------------------------------------------------------------------- #

FIXTURE_SAFE = """
USB:

    USB 3.1 Bus:

      Host Controller Driver: AppleT8103USBXHCI

        BOOTMUX Keyboard Safe:

          Product ID: 0x0001
          Vendor ID: 0x303a
          Version: 1.00
          Serial Number: BOOTMUX-HID-SAFE
          Speed: Up to 12 Mb/s
          Manufacturer: BOOTMUX
          Product: BOOTMUX Keyboard Safe
          Location ID: 0x00100000
          Current Available (mA): 500
          USB Interface Class: HID
"""

FIXTURE_NETWORK = """
USB:

    USB 3.1 Bus:

        BOOTMUX Device:

          Product ID: 0x0002
          Vendor ID: 0x303a
          Serial Number: BOOTMUX-HID-SAFE
          Product: BOOTMUX Device
          USB Interface Class: CDC-ECM Network
"""

FIXTURE_NONE = """
USB:

    USB 3.1 Bus:

        Apple Internal Keyboard:

          Product ID: 0x0003
          Product: Apple Internal Keyboard
"""


def selftest():
    checks = []

    safe = classify_bootmux(parse_usb_devices(FIXTURE_SAFE))
    checks.append(("safe fixture -> SAFE_HID_ONLY", safe["verdict"] == "SAFE_HID_ONLY", safe["verdict"]))
    checks.append(("safe fixture product_is_safe", safe["product_is_safe"] is True, safe["product_is_safe"]))
    checks.append(("safe fixture serial_is_safe", safe["serial_is_safe"] is True, safe["serial_is_safe"]))
    checks.append(("safe fixture hid_present", safe["hid_present"] is True, safe["hid_present"]))
    checks.append(("safe fixture network_class_absent", safe["network_class_absent"] is True, safe["network_class_absent"]))

    net = classify_bootmux(parse_usb_devices(FIXTURE_NETWORK))
    checks.append(("network fixture -> NETWORK_CLASS_PRESENT", net["verdict"] == "NETWORK_CLASS_PRESENT", net["verdict"]))
    checks.append(("network fixture network_class_absent False", net["network_class_absent"] is False, net["network_class_absent"]))

    none = classify_bootmux(parse_usb_devices(FIXTURE_NONE))
    checks.append(("none fixture -> NO_BOOTMUX_DEVICE", none["verdict"] == "NO_BOOTMUX_DEVICE", none["verdict"]))

    ok = all(passed for _, passed, _ in checks)
    for name, passed, got in checks:
        print(f"  {'ok  ' if passed else 'FAIL'} {name} (got={got})")
    print("USB_IDENTITY_SELFTEST=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def live():
    result = subprocess.run(
        ["system_profiler", "SPUSBDataType"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        print("ERROR: system_profiler failed", file=sys.stderr)
        return 2
    verdict = classify_bootmux(parse_usb_devices(result.stdout))
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["verdict"] in ("SAFE_HID_ONLY", "NO_BOOTMUX_DEVICE") else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R7C P4 USB identity oracle (read-only)")
    parser.add_argument("cmd", choices=["live", "selftest"])
    args = parser.parse_args(argv)
    if args.cmd == "selftest":
        return selftest()
    return live()


if __name__ == "__main__":
    sys.exit(main())
