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
    require(
        errors,
        "USB HID-only" in router_readme and "must not enumerate a USB Ethernet interface" in router_readme,
        "router-spike README no longer documents the host-network-safe default",
    )
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
