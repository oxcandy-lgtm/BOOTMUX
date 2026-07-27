#!/usr/bin/env python3
"""R7C P4 — serial marker oracle (read-only).

Checks captured firmware serial output for the required R7C markers and the
absence of panic/watchdog/brownout markers.  The checker is a pure function
over text so it can be proven with fixtures; the CLI reads a captured log file.

Safe-profile required markers:
  BOOTMUX_USB_NETWORK_SAFE_OFF

Panic-class markers that must be ABSENT:
  Guru Meditation Error, panic, watchdog, brownout, abort(), Backtrace:

Commands:
  check FILE   check a captured serial log file
  selftest     run built-in fixture checks (no device, no file I/O)
"""

import argparse
import json
import sys

SAFE_REQUIRED = ["BOOTMUX_USB_NETWORK_SAFE_OFF"]

EXPERIMENTAL_REQUIRED = [
    "BOOTMUX_USB_NETIF_DOWN_AT_BOOT_EXPERIMENTAL",
    "BOOTMUX_USB_NETWORK_NO_DHCP_NO_DEFAULT_ROUTE",
]

PANIC_MARKERS = [
    "guru meditation error",
    "panic",
    "watchdog",
    "brownout",
    "abort()",
    "backtrace:",
    "core  0 panic",
    "core  1 panic",
]


def check_serial_log(text: str, profile: str = "safe"):
    """Pure function: return a verdict dict for captured serial text."""
    lower = text.lower()

    if profile == "safe":
        required = SAFE_REQUIRED
    elif profile == "experimental":
        required = EXPERIMENTAL_REQUIRED
    else:
        required = []

    found_required = {m: m in text for m in required}
    missing_required = [m for m, present in found_required.items() if not present]

    panic_found = [m for m in PANIC_MARKERS if m in lower]

    if missing_required:
        verdict = "MISSING_REQUIRED_MARKERS"
    elif panic_found:
        verdict = "PANIC_DETECTED"
    else:
        verdict = "CLEAN"

    return {
        "profile": profile,
        "required_markers": found_required,
        "missing_required": missing_required,
        "panic_markers_found": panic_found,
        "verdict": verdict,
    }


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

FIXTURE_SAFE_CLEAN = """
I (312) main_task: Started on CPU0
I (312) BOOTMUX: USB descriptors loaded
I (313) BOOTMUX: BOOTMUX_USB_NETWORK_SAFE_OFF
I (314) main_task: Calling app_main()
"""

FIXTURE_SAFE_PANIC = """
I (312) BOOTMUX: BOOTMUX_USB_NETWORK_SAFE_OFF
Guru Meditation Error: Core  0 panic'ed (LoadProhibited)
Backtrace: 0x400d1234:0x3ffb5678
"""

FIXTURE_SAFE_MISSING = """
I (312) main_task: Started on CPU0
I (313) BOOTMUX: USB descriptors loaded
"""

FIXTURE_EXP_CLEAN = """
I (312) BOOTMUX: BOOTMUX_USB_NETIF_DOWN_AT_BOOT_EXPERIMENTAL
I (313) BOOTMUX: BOOTMUX_USB_NETWORK_NO_DHCP_NO_DEFAULT_ROUTE
I (314) main_task: Calling app_main()
"""


def selftest():
    checks = []

    r = check_serial_log(FIXTURE_SAFE_CLEAN, "safe")
    checks.append(("safe clean -> CLEAN", r["verdict"] == "CLEAN", r["verdict"]))

    r = check_serial_log(FIXTURE_SAFE_PANIC, "safe")
    checks.append(("safe panic -> PANIC_DETECTED", r["verdict"] == "PANIC_DETECTED", r["verdict"]))
    checks.append(("safe panic markers found", len(r["panic_markers_found"]) >= 2, r["panic_markers_found"]))

    r = check_serial_log(FIXTURE_SAFE_MISSING, "safe")
    checks.append(("safe missing -> MISSING_REQUIRED_MARKERS", r["verdict"] == "MISSING_REQUIRED_MARKERS", r["verdict"]))

    r = check_serial_log(FIXTURE_EXP_CLEAN, "experimental")
    checks.append(("exp clean -> CLEAN", r["verdict"] == "CLEAN", r["verdict"]))

    ok = all(passed for _, passed, _ in checks)
    for name, passed, got in checks:
        print(f"  {'ok  ' if passed else 'FAIL'} {name} (got={got})")
    print("SERIAL_MARKER_SELFTEST=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R7C P4 serial marker oracle (read-only)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="check a captured serial log file")
    p_check.add_argument("file")
    p_check.add_argument("--profile", choices=["safe", "experimental"], default="safe")
    sub.add_parser("selftest", help="run built-in fixture checks")
    args = parser.parse_args(argv)

    if args.cmd == "selftest":
        return selftest()

    if args.cmd == "check":
        try:
            text = open(args.file).read()
        except OSError as e:
            print(f"ERROR: cannot read {args.file}: {e}", file=sys.stderr)
            return 2
        verdict = check_serial_log(text, args.profile)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 0 if verdict["verdict"] == "CLEAN" else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
