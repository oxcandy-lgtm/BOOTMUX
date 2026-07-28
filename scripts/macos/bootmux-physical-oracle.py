#!/usr/bin/env python3
"""R7C P4 — read-only physical-acceptance oracle (sanitized evidence).

This tool observes the Mac's network state and compares it against a captured
baseline WITHOUT mutating anything.  It exists because P4 requires physical
proof that the safe profile leaves the host invariant and that the Guardian
restores the baseline — and that proof must be sanitized (no SSID, MAC, IP,
gateway, DNS server, or credential may appear in committed evidence).

Privacy model (stricter than the Guardian baseline):
  * Wi-Fi SSID            -> sha256 token (12 hex), never plaintext
  * MAC / hardware addr   -> "<mac>"
  * IPv4 address / router -> class token (e.g. "192.168.x.x") or "<ip>"
  * DNS servers / search  -> count + per-item sha256 tokens
  * BOOTMUX routes        -> listed (these are the test's own, non-private)

Commands:
  capture            print a sanitized snapshot of the current state (stdout)
  baseline FILE      capture and write a sanitized baseline to FILE
  compare FILE       compare current state to baseline FILE; exit 0 iff all
                     invariants hold, 1 on any violation, 2 on usage error

The tool never runs networksetup/scutil/route with mutating arguments; it only
reads.  It is safe to run at any point in the P4 sequence.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

# Reuse the Guardian's SystemHost primitives and baseline capture.
_GUARDIAN = Path(__file__).resolve().parent / "bootmux-network-guardian.py"
_spec = importlib.util.spec_from_file_location("bootmux_network_guardian", _GUARDIAN)
assert _spec is not None and _spec.loader is not None, f"cannot load guardian: {_GUARDIAN}"
guardian = importlib.util.module_from_spec(_spec)
sys.modules["bootmux_network_guardian"] = guardian
_spec.loader.exec_module(guardian)


# --------------------------------------------------------------------------- #
# Sanitization helpers
# --------------------------------------------------------------------------- #

def _token(value) -> str:
    """Stable, non-reversible identifier token (never plaintext)."""
    if value is None:
        return "<none>"
    return "tok:" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def _ip_class(value):
    """Reduce an IPv4 address to its class token; hide the host bits."""
    if not value:
        return "<none>"
    parts = str(value).split(".")
    if len(parts) != 4:
        return "<ip>"
    a, b = parts[0], parts[1]
    if a == "169":
        return "169.254.x.x(link-local)"
    if a == "10":
        return "10.x.x.x(private)"
    if a == "192" and b == "168":
        return "192.168.x.x(private)"
    if a == "172" and b.isdigit() and 16 <= int(b) <= 31:
        return "172.16-31.x.x(private)"
    return "<ip>"


def _read_default_route(host):
    """Read the default route directly (the Guardian routes() parser skips the
    literal 'default' destination row).  Returns (interface, gateway_class)."""
    rc, out, _ = host.run(["route", "-n", "get", "default"])
    iface = None
    gw = None
    if rc == 0:
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("interface:"):
                iface = line.split(":", 1)[1].strip()
            elif line.startswith("gateway:"):
                gw = line.split(":", 1)[1].strip()
    return iface, _ip_class(gw)


def sanitize_snapshot(host) -> dict:
    """Capture current state via the Guardian host and sanitize every field."""
    base = guardian.capture_baseline(host)
    wifi = base.get("wifi", {})
    net = base.get("network", {})

    # Authoritative default route (Guardian routes() omits the 'default' row).
    default_iface, default_gw_class = _read_default_route(host)

    san_wifi = {
        "hardware_device": wifi.get("hardware_device"),
        "service_name": wifi.get("service_name"),
        "power": wifi.get("power"),
        "ssid_token": _token(wifi.get("associated_ssid")),
        "associated": wifi.get("associated_ssid") is not None,
        "ipv4_mode": wifi.get("ipv4_mode"),
        "ipv4_class": _ip_class(wifi.get("ipv4_address")),
        "router_class": _ip_class(wifi.get("router")),
        "dns_server_count": len(wifi.get("dns_servers") or []),
        "dns_server_tokens": [_token(s) for s in (wifi.get("dns_servers") or [])],
        "search_domain_count": len(wifi.get("search_domains") or []),
    }
    san_net = {
        "default_gateway_class": default_gw_class,
        "default_interface": default_iface,
        "network_service_order": net.get("network_service_order", []),
        "service_enabled_states": net.get("service_enabled_states", {}),
        "bootmux_routes": net.get("bootmux_routes", []),
    }

    # BOOTMUX-related services (the test's own artifacts; non-private).
    bootmux_services = [
        name for name in san_net["network_service_order"]
        if "bootmux" in name.lower()
    ]

    return {
        "schema_version": 1,
        "tool": "bootmux-physical-oracle",
        "captured_at": base.get("captured_at"),
        "wifi": san_wifi,
        "network": san_net,
        "bootmux_services": bootmux_services,
        "redaction": [
            "wifi.ssid->token", "wifi.ipv4->class", "wifi.router->class",
            "wifi.dns->tokens", "network.default_gateway->class",
            "mac->never-captured",
        ],
    }


# --------------------------------------------------------------------------- #
# Invariant comparison
# --------------------------------------------------------------------------- #

# Fields that must be EQUAL between baseline and current for the host to be
# considered "unchanged" by a safe-profile attach/detach cycle.
INVARIANT_FIELDS = [
    ("wifi.power", lambda s: s["wifi"]["power"]),
    ("wifi.ssid_token", lambda s: s["wifi"]["ssid_token"]),
    ("wifi.ipv4_mode", lambda s: s["wifi"]["ipv4_mode"]),
    ("wifi.dns_server_count", lambda s: s["wifi"]["dns_server_count"]),
    ("wifi.dns_server_tokens", lambda s: s["wifi"]["dns_server_tokens"]),
    ("network.default_interface", lambda s: s["network"]["default_interface"]),
    ("network.default_gateway_class", lambda s: s["network"]["default_gateway_class"]),
    ("network.network_service_order", lambda s: s["network"]["network_service_order"]),
    ("network.service_enabled_states", lambda s: s["network"]["service_enabled_states"]),
]


def compare_invariants(baseline: dict, current: dict, require_clean: bool = False):
    """Return (violations, report_lines).

    The core gate is BASELINE EQUALITY: every invariant field must be equal
    between baseline and current.  This proves a safe-profile cycle changed
    nothing, or that the Guardian restored the baseline.

    When require_clean=True (used at the safe-profile attach gate), BOOTMUX
    routes/services must additionally be ABSENT.  Pre-existing BOOTMUX services
    captured in the baseline do NOT violate baseline equality.
    """
    violations = []
    lines = []
    for name, getter in INVARIANT_FIELDS:
        try:
            b = getter(baseline)
            c = getter(current)
        except (KeyError, TypeError):
            violations.append(name)
            lines.append(f"  VIOLATION {name}: field unreadable")
            continue
        if b != c:
            violations.append(name)
            lines.append(f"  VIOLATION {name}: baseline={b!r} current={c!r}")
        else:
            lines.append(f"  ok        {name}")

    # BOOTMUX routes must always be absent (the safe profile never adds one,
    # and the Guardian removes them on recovery).
    bm_routes = current["network"].get("bootmux_routes", [])
    if bm_routes:
        violations.append("bootmux_routes_absent")
        lines.append(f"  VIOLATION bootmux routes present: {bm_routes}")
    else:
        lines.append("  ok        bootmux_routes_absent")

    # BOOTMUX services: only a violation when a clean state is required.
    bm_services = current.get("bootmux_services", [])
    if require_clean:
        if bm_services:
            violations.append("bootmux_services_absent")
            lines.append(f"  VIOLATION bootmux services present: {bm_services}")
        else:
            lines.append("  ok        bootmux_services_absent")
    else:
        lines.append(f"  info      bootmux_services={bm_services} (not gated; baseline equality covers it)")

    return violations, lines


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R7C P4 physical-acceptance oracle (read-only)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture", help="print sanitized current state")
    p_base = sub.add_parser("baseline", help="write sanitized baseline to FILE")
    p_base.add_argument("file")
    p_cmp = sub.add_parser("compare", help="compare current state to baseline FILE")
    p_cmp.add_argument("file")
    p_cmp.add_argument("--require-clean", action="store_true",
                       help="also require BOOTMUX services absent (safe-attach gate)")
    args = parser.parse_args(argv)

    host = guardian.SystemHost()

    if args.cmd == "capture":
        print(json.dumps(sanitize_snapshot(host), indent=2, sort_keys=True))
        return 0

    if args.cmd == "baseline":
        snap = sanitize_snapshot(host)
        Path(args.file).write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n")
        print(f"baseline written: {args.file}")
        print(f"  ssid_token={snap['wifi']['ssid_token']} default_interface={snap['network']['default_interface']}")
        return 0

    if args.cmd == "compare":
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: baseline file not found: {args.file}", file=sys.stderr)
            return 2
        baseline = json.loads(path.read_text())
        current = sanitize_snapshot(host)
        violations, lines = compare_invariants(baseline, current, require_clean=args.require_clean)
        print("invariant comparison (current vs baseline):")
        for line in lines:
            print(line)
        if violations:
            print(f"RESULT=VIOLATION fields={violations}")
            return 1
        print("RESULT=INVARIANTS_HOLD")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
