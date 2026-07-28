#!/usr/bin/env python3
"""Fail when public BOOTMUX contracts drift across code and documentation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORE_SERVICE = "7c1b0001-4b4f-4d55-9a01-42584d583101"
CORE_RX = "7c1b0002-4b4f-4d55-9a01-42584d583101"
CORE_TX = "7c1b0003-4b4f-4d55-9a01-42584d583101"
ROUTER_RX = "7c1b0002-4b4f-4d55-9a01-42584d583102"
ROUTER_TX = "7c1b0003-4b4f-4d55-9a01-42584d583103"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def contains_casefold(text: str, value: str) -> bool:
    return value.casefold() in text.casefold()


# ---------------------------------------------------------------------------
# R7C P3 — whitespace-robust prose helpers.
#
# Prose / Markdown contracts (README, docs) wrap across lines, so an exact
# contiguous-substring search false-negatives accurate prose.  These helpers
# collapse every whitespace run to a single space before a semantic phrase
# check.  They are used ONLY for prose; source-code and sdkconfig checks keep
# their exact-syntax matching.
# ---------------------------------------------------------------------------

def normalize_prose(text: str) -> str:
    """Collapse all whitespace runs (incl. newlines) to single spaces and strip
    inline Markdown formatting (bold, italic, code) so semantic phrases match
    regardless of emphasis markup."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)   # **bold**
    text = re.sub(r"\*([^*]+)\*", r"\1", text)        # *italic*
    text = re.sub(r"`([^`]+)`", r"\1", text)          # `code`
    return re.sub(r"\s+", " ", text).strip()


def prose_contains(text: str, phrase: str) -> bool:
    """True iff `phrase` appears in `text` ignoring whitespace reflow."""
    return normalize_prose(phrase) in normalize_prose(text)


def _function_body(source: str, signature_regex: str) -> str:
    """Return the brace-balanced body of the first function matching the regex.

    Used so gate/teardown contracts are checked inside the relevant function
    only, not against identifiers that also appear in unrelated helpers.
    Returns "" when not found.
    """
    match = re.search(signature_regex, source)
    if not match:
        return ""
    start = source.find("{", match.end())
    if start == -1:
        return ""
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    return ""


# ---------------------------------------------------------------------------
# R7C P3 — dedicated contract checks, as pure functions over file contents.
#
# Each returns a list of error strings (empty == contract holds).  main() feeds
# them the real tree; the mutation tests feed them in-memory broken variants.
# ---------------------------------------------------------------------------

def r7c_readme_errors(readme: str) -> list[str]:
    """Host-network-safe default must be documented (whitespace-robust)."""
    errors: list[str] = []
    for phrase in (
        "USB HID-only",
        "must not enumerate a USB Ethernet interface",
        "does not run a DHCP server",
        "no configured gateway",
        "does not provide DNS",
    ):
        if not prose_contains(readme, phrase):
            errors.append(f"router-spike README lost host-network-safe contract phrase: {phrase!r}")
    return errors


def r7c_safe_default_errors(sdkconfig: str, descriptors: str, usb_router: str) -> list[str]:
    """Normal build must stay HID-only: no network mode, no forwarding, safe marker."""
    errors: list[str] = []
    # Safe sdkconfig: network modes and forwarding all off, experiment off.
    if "CONFIG_TINYUSB_NET_MODE_NONE=y" not in sdkconfig:
        errors.append("safe sdkconfig no longer selects TinyUSB network mode None")
    for forbidden in (
        "CONFIG_TINYUSB_NET_MODE_NCM=y",
        "CONFIG_TINYUSB_NET_MODE_ECM_RNDIS=y",
        "CONFIG_LWIP_IP_FORWARD=y",
        "CONFIG_LWIP_IPV4_NAPT=y",
    ):
        if forbidden in sdkconfig:
            errors.append(f"safe sdkconfig unexpectedly enables {forbidden}")
    if "# CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL is not set" not in sdkconfig:
        errors.append("safe sdkconfig no longer keeps USB networking default-off")
    if re.search(r"config BOOTMUX_USB_NETWORK_EXPERIMENTAL.*?default y", sdkconfig, re.S):
        errors.append("CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL became default-on")
    # Safe descriptor: distinct HID-only identity, no network interface class.
    if "BOOTMUX Keyboard Safe" not in descriptors or "BOOTMUX-HID-SAFE" not in descriptors:
        errors.append("safe USB descriptor lost the distinct HID-only identity")
    # Safe marker present in firmware.
    if "BOOTMUX_USB_NETWORK_SAFE_OFF" not in usb_router:
        errors.append("safe marker BOOTMUX_USB_NETWORK_SAFE_OFF disappeared")
    return errors


def r7c_experimental_errors(usb_router: str, exp_sdkconfig: str, runtime_c: str) -> list[str]:
    """Experimental profile: no DHCP server, no gw/DNS, not authoritative at boot,
    no direct activation outside the reconciler."""
    errors: list[str] = []
    if "ESP_NETIF_DHCP_SERVER" in usb_router:
        errors.append("USB experiment reintroduced a DHCP server")
    if ".gw = { .addr = 0 }" not in usb_router or "BOOTMUX_USB_NETWORK_NO_DHCP_NO_DEFAULT_ROUTE" not in usb_router:
        errors.append("USB experiment can again advertise a gateway/default route")
    if "BOOTMUX_USB_NETIF_DOWN_AT_BOOT_EXPERIMENTAL" not in usb_router:
        errors.append("USB netif is no longer documented DOWN at boot")
    # Experiment profile must still be the explicit opt-in.
    if "CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL=y" not in exp_sdkconfig:
        errors.append("explicit USB-network experiment profile lost its opt-in flag")
    # GOT_IP must route through the reconciler, never start the router directly.
    got_ip = _function_body(runtime_c, r"static void wifi_task\b")
    if got_ip and "IP_EVENT_STA_GOT_IP" in got_ip:
        branch = got_ip.split("IP_EVENT_STA_GOT_IP", 1)[1]
        if "reconcile_management_path" not in branch:
            errors.append("IP_EVENT_STA_GOT_IP no longer reaches the reconciler")
        if "bootmux_usb_router_start" in branch:
            errors.append("network activation happens directly from IP_EVENT_STA_GOT_IP outside the reconciler")
    return errors


def r7c_p1_gate_errors(mgmt_c: str, mgmt_h: str, probe_c: str, runtime_c: str) -> list[str]:
    """Four-condition AND gate, bounded 60s lease, fixed allowlist, reverse teardown,
    fail-closed boot, and every withdrawal trigger reaching reconciliation."""
    errors: list[str] = []
    # All four conditions inside the open predicate.
    should_open = _function_body(mgmt_c, r"bool mg_should_open\b")
    for condition in ("wifi_has_ip", "target_reachable", "allowlist_loaded", "mg_lease_active"):
        if condition not in should_open:
            errors.append(f"P1 gate condition removed from mg_should_open: {condition}")
    # Bounded lease: TTL window fixed at 10..60 and enforced on grant.
    if not re.search(r"#define\s+MG_LEASE_TTL_MAX\s+60\b", mgmt_h):
        errors.append("management lease max TTL is no longer the bounded 60 seconds")
    if not re.search(r"#define\s+MG_LEASE_TTL_MIN\s+10\b", mgmt_h):
        errors.append("management lease min TTL drifted from 10 seconds")
    grant = _function_body(mgmt_c, r"bool mg_lease_grant\b")
    if grant and "MG_LEASE_TTL_MAX" not in grant:
        errors.append("management lease grant no longer enforces the bounded TTL")
    # Fixed compile-time allowlist: exactly the two sanctioned literals, no DNS.
    allowlist = {tuple(int(x) for x in m) for m in re.findall(r"TP_IPV4\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", probe_c)}
    if allowlist != {(192, 168, 11, 1), (192, 168, 77, 1)}:
        errors.append(f"target allowlist widened or drifted: {sorted(allowlist)}")
    if re.search(r"getaddrinfo|gethostbyname|esp_netif.*dns", probe_c, re.I):
        errors.append("target allowlist accepts DNS resolution instead of fixed literals")
    # Teardown order is the strict reverse: proxy -> NAPT -> netif.
    deactivate = _function_body(mgmt_c, r"static void deactivate\b")
    if deactivate:
        positions = {name: deactivate.find(name) for name in ("proxy_stop", "napt_disable", "netif_stop")}
        if any(p == -1 for p in positions.values()):
            errors.append(f"teardown missing a step: {positions}")
        elif not (positions["proxy_stop"] < positions["napt_disable"] < positions["netif_stop"]):
            errors.append(f"teardown order is no longer proxy -> NAPT -> netif: {positions}")
    # Boot state is fail-closed DOWN.
    if "BOOTMUX_USB_NETIF_DOWN_AT_BOOT_EXPERIMENTAL" not in runtime_c and "BOOTMUX_USB_NETIF_DOWN_AT_BOOT_EXPERIMENTAL" not in mgmt_c:
        # marker lives in usb_router.c; boot-DOWN contract is asserted there via
        # r7c_experimental_errors.  Here we only assert the gate starts closed.
        pass
    init = _function_body(mgmt_c, r"void mg_init\b")
    if init and "path_open = false" not in init and "path_open=false" not in init:
        # mg_init zero-closes the path; accept explicit or documented closed boot.
        if "MG_REASON_BOOT" not in init:
            errors.append("gate boot state is not fail-closed")
    # Every withdrawal trigger reaches reconciliation / lease release.
    for trigger in ("WIFI_EVENT_STA_DISCONNECTED", "IP_EVENT_STA_GOT_IP", "NET_RELEASE", "WIFI_CLEAR"):
        if trigger not in runtime_c:
            errors.append(f"withdrawal trigger no longer wired: {trigger}")
    if "mg_lease_release" not in runtime_c:
        errors.append("NET_RELEASE/WIFI_CLEAR/BLE disconnect no longer drop the lease")
    if "reconcile_management_path" not in runtime_c:
        errors.append("lifecycle events no longer reach reconciliation")
    return errors


def r7c_p2_guardian_errors(guardian_py: str) -> list[str]:
    """Mac Guardian: identity-gated mutation, no destructive host operations,
    hardened state store, SSID redaction, bounded Wi-Fi toggle."""
    errors: list[str] = []
    # Identity proof gates mutation; ambiguous fails closed to audit-only.
    if "def prove_identity" not in guardian_py:
        errors.append("Guardian identity proof removed")
    if "ambiguous" not in guardian_py or "audit-only" not in guardian_py:
        errors.append("ambiguous identity no longer fails closed to audit-only")
    # No global route flush (file/stderr .flush() calls are benign; match route -f).
    if re.search(r"route[\"'\s,]+-f\b|flush.*routing|routeflush", guardian_py, re.I):
        errors.append("Guardian gained a global routing-table flush")
    # No network service deletion.
    if re.search(r"-removenetworkservice|removeservice|delete_network_service", guardian_py, re.I):
        errors.append("Guardian can delete a network service")
    # No direct SystemConfiguration preference editing.
    if "/Library/Preferences/SystemConfiguration" in guardian_py:
        errors.append("Guardian edits /Library/Preferences/SystemConfiguration directly")
    # No saved Wi-Fi network deletion.
    if re.search(r"removepreferredwirelessnetwork|forget.*saved|delete.*saved.*wi-?fi", guardian_py, re.I):
        errors.append("Guardian can delete saved Wi-Fi networks")
    # Hardened state store validation.
    for token, what in (
        ("os.path.islink", "symlink"),
        ("0o700", "mode"),
        ("st_uid", "owner"),
        ("schema_version", "schema"),
    ):
        if token not in guardian_py:
            errors.append(f"state store lost {what} validation ({token})")
    # SSID redaction present.
    if "redact_baseline" not in guardian_py or "<redacted>" not in guardian_py:
        errors.append("SSID redaction removed from status/log output")
    # Wi-Fi toggle stays a bounded last resort.
    if "cooldown" not in guardian_py:
        errors.append("Wi-Fi toggle lost its last-resort/cooldown bound")
    return errors


def main() -> int:
    errors: list[str] = []

    swift = read("iphone/BOOTMUX/BLEProtocol.swift")
    content_view = read("iphone/BOOTMUX/ContentView.swift")
    iphone_readme = read("iphone/README.md")
    bridge = read("firmware/esp32s3-bridge/src/main.cpp")
    bridge_readme = read("firmware/esp32s3-bridge/README.md")
    router_kconfig = read("firmware/esp32s3-router-spike/main/Kconfig.projbuild")
    router_sdkconfig = read("firmware/esp32s3-router-spike/sdkconfig.defaults")
    router_experimental_sdkconfig = read("firmware/esp32s3-router-spike/sdkconfig.usb-network.defaults")
    router_descriptors = read("firmware/esp32s3-router-spike/main/usb_descriptors.c")
    router_usb = read("firmware/esp32s3-router-spike/main/usb_router.c")
    router_readme = read("firmware/esp32s3-router-spike/README.md")
    mac_recovery = read("scripts/macos/recover-bootmux-usb-network.sh")
    bmx1 = read("docs/protocol/BMX1.md")
    server = read("companion/server.go")
    companion_protocol = read("docs/COMPANION_PROTOCOL_V1.md")
    root_readme = read("README.md")
    judge_readme = read("judge/README.md")
    # R7C P3 — firmware gate + Mac Guardian sources for dedicated contract checks.
    mgmt_c = read("firmware/esp32s3-router-spike/main/management_gate.c")
    mgmt_h = read("firmware/esp32s3-router-spike/main/management_gate.h")
    probe_c = read("firmware/esp32s3-router-spike/main/target_probe.c")
    runtime_c = read("firmware/esp32s3-router-spike/main/ble_wifi_runtime.c")
    guardian_py = read("scripts/macos/bootmux-network-guardian.py")

    for label, value in (
        ("core service UUID", CORE_SERVICE),
        ("core RX UUID", CORE_RX),
        ("core TX UUID", CORE_TX),
    ):
        require(errors, contains_casefold(swift, value), f"Swift missing {label}: {value}")
        require(errors, contains_casefold(bridge, value), f"core firmware missing {label}: {value}")
        require(errors, contains_casefold(bridge_readme, value), f"bridge README missing {label}: {value}")
        require(errors, contains_casefold(bmx1, value), f"BMX1 doc missing {label}: {value}")

    for label, value in (("router RX UUID", ROUTER_RX), ("router TX UUID", ROUTER_TX)):
        require(errors, contains_casefold(bmx1, value), f"BMX1 doc missing {label}: {value}")

    require(
        errors,
        'static let rxUUID = "7C1B0002-4B4F-4D55-9A01-42584D583101"' in swift,
        "Swift active RX UUID is not the demonstrated core keyboard profile",
    )
    require(
        errors,
        'static let txUUID = "7C1B0003-4B4F-4D55-9A01-42584D583101"' in swift,
        "Swift active TX UUID is not the demonstrated core keyboard profile",
    )

    require(
        errors,
        'Section("Network Bridge — Experimental")' in content_view,
        "iPhone Settings no longer labels router controls experimental",
    )
    require(
        errors,
        "Router-spike profile required. Disabled in this Build Week core keyboard build." in content_view,
        "iPhone Settings missing the router-profile boundary warning",
    )
    require(
        errors,
        re.search(r"var\s+isOpenForWiFi:\s*Bool\s*\{\s*false\s*\}", content_view) is not None,
        "router mutation controls are not fail-closed in the core iPhone build",
    )
    require(
        errors,
        ".onAppear {\n            if endpoint.isEmpty { endpoint = lastSuccessfulEndpoint }\n            ble.forgetSavedWiFi()\n        }" in content_view,
        "core iPhone build no longer clears inactive router credentials at launch",
    )
    require(
        errors,
        "## Experimental router controls" in iphone_readme,
        "iPhone README missing the experimental router boundary",
    )

    # Normal S3 attachment must be host-network inert. USB Ethernet is an
    # explicit research profile, never a default side effect of keyboard use.
    require(
        errors,
        "config BOOTMUX_USB_NETWORK_EXPERIMENTAL" in router_kconfig
        and re.search(r"config BOOTMUX_USB_NETWORK_EXPERIMENTAL.*?default n", router_kconfig, re.S) is not None,
        "router-spike USB networking is no longer opt-in/default-off",
    )
    require(
        errors,
        "CONFIG_TINYUSB_NET_MODE_NONE=y" in router_sdkconfig,
        "normal router-spike build no longer selects TinyUSB network mode None",
    )
    require(
        errors,
        "CONFIG_TINYUSB_NET_MODE_NCM=y" not in router_sdkconfig,
        "normal router-spike build unexpectedly enables NCM",
    )
    require(
        errors,
        "# CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL is not set" in router_sdkconfig,
        "normal router-spike build unexpectedly enables USB networking",
    )
    require(
        errors,
        "CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL=y" in router_experimental_sdkconfig
        and "CONFIG_TINYUSB_NET_MODE_NCM=y" in router_experimental_sdkconfig,
        "explicit USB-network experiment profile is incomplete",
    )
    require(
        errors,
        "#if CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL" in router_descriptors
        and ".iSerialNumber = BOOTMUX_STR_SERIAL" in router_descriptors
        and "BOOTMUX Keyboard Safe" in router_descriptors,
        "USB descriptors no longer enforce a distinct HID-only safe profile",
    )
    require(
        errors,
        "ESP_NETIF_DHCP_SERVER" not in router_usb,
        "USB experiment reintroduced a DHCP server that can hijack host routing",
    )
    require(
        errors,
        ".gw = { .addr = 0 }" in router_usb
        and "BOOTMUX_USB_NETWORK_NO_DHCP_NO_DEFAULT_ROUTE" in router_usb,
        "USB experiment can again advertise itself as a host default route",
    )
    require(
        errors,
        "BOOTMUX_USB_NETWORK_SAFE_OFF" in router_usb,
        "normal firmware is missing the USB-network-safe marker",
    )
    # R7C P3 — whitespace-robust README contract (replaces the brittle exact
    # substring check that false-negatived accurate prose wrapped across a
    # Markdown line break).  Contract is preserved, not weakened.
    errors.extend(r7c_readme_errors(router_readme))
    # R7C P3 — dedicated firmware + Guardian contract checks (pure functions).
    errors.extend(r7c_safe_default_errors(router_sdkconfig, router_descriptors, router_usb))
    errors.extend(r7c_experimental_errors(router_usb, router_experimental_sdkconfig, runtime_c))
    errors.extend(r7c_p1_gate_errors(mgmt_c, mgmt_h, probe_c, runtime_c))
    errors.extend(r7c_p2_guardian_errors(guardian_py))
    require(
        errors,
        "10.77.0.1" in mac_recovery
        and "-setairportpower" in mac_recovery
        and "-setnetworkserviceenabled" in mac_recovery,
        "macOS no-reboot recovery script lost required controls",
    )

    for frame in ("BMX1|OPEN", "BMX1|TEXT", "BMX1|CTRL", "BMX1|ACK", "BMX1|ERR"):
        require(errors, frame in bmx1, f"BMX1 doc missing core frame {frame}")

    for endpoint in ('"/v1/terminal"', '"/v1/mirror"', '"/judge"'):
        require(errors, endpoint in server, f"Companion server missing endpoint {endpoint}")

    for expected in (
        "defaultCodexOutput      = 128 * 1024",
        "defaultCodexPrompt      = 8 * 1024",
        "defaultCodexTimeout     = 180 * time.Second",
        "maxWebSocketMessage     = 16 * 1024",
        "maxJSONMessage          = 12 * 1024",
        "maxInputTextBytes       = 8 * 1024",
    ):
        require(errors, expected in server, f"Companion bound drifted: {expected}")

    for documented in ("16 KiB", "12 KiB", "8 KiB", "128 KiB", "180 seconds"):
        require(errors, documented in companion_protocol, f"Companion protocol doc missing bound: {documented}")

    require(errors, "127.0.0.1:8765" in root_readme, "root README live Judge port drifted")
    require(errors, "127.0.0.1:8765" in judge_readme, "Judge README live port drifted")
    require(errors, "/v1/terminal" in companion_protocol, "Companion protocol endpoint missing")

    stale_current_state_patterns = {
        "docs/NEXT_IMPLEMENTATION_TASK.md": (
            r"Keep PR #1 Draft, open, and unmerged",
            r"branch:\s*agent/bootstrap-design-roadmap",
        ),
        "docs/ROADMAP.md": (
            r"AWAITING_HUMAN_AUTH",
            r"AWAITING_PHYSICAL_IPHONE_RETURN",
        ),
    }
    for relative, patterns in stale_current_state_patterns.items():
        text = read(relative)
        for pattern in patterns:
            require(errors, re.search(pattern, text) is None, f"stale current-state text in {relative}: {pattern}")

    if errors:
        print("BOOTMUX_CONTRACT_SYNC=FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("BOOTMUX_CONTRACT_SYNC=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
