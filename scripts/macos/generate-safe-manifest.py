#!/usr/bin/env python3
"""R7C P4-R1C — regenerate safe-flash-manifest.json from a build directory.

Usage:
    python3 generate-safe-manifest.py <build_dir> [--output <path>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_marker(lines: str, key: str) -> str:
    """
    Detect the exact config-not-set line for a boolean KEY.
    In sdkconfig, unset bools appear as: '# CONFIG_XXX is not set'
    Overwritten bools appear as: 'CONFIG_XXX=y' or 'CONFIG_XXX=true'
    We return the exact string found, or ''.
    """
    for line in lines.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"# {key} is not set"):
            return stripped
    return ""


def extract_sdkconfig_marker(sdkconfig_path: Path) -> str:
    """Extract the BOOTMUX_USB_NETWORK_EXPERIMENTAL marker line."""
    if not sdkconfig_path.exists():
        return ""
    return detect_marker(sdkconfig_path.read_text(errors="replace"),
                         "CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL")


def generate_manifest(build_dir: Path, output_path: Path) -> Dict[str, Any]:
    build_dir = build_dir.resolve()

    # Read flasher_args.json (contains offset/size metadata)
    flasher_path = build_dir / "flasher_args.json"
    if not flasher_path.exists():
        print(f"ERROR: no flasher_args.json in {build_dir}", file=sys.stderr)
        sys.exit(1)

    with open(flasher_path) as f:
        flasher = json.load(f)

    flash_settings = flasher.get("flash_settings", {})
    flash_files = flasher.get("flash_files", {})

    # Build artifacts list
    artifacts = []
    name_map = {
        "0x0": "bootloader",
        "0x8000": "partition-table",
        "0x10000": "application",
    }

    for offset_str in sorted(flash_files.keys(), key=lambda x: int(x, 16)):
        rel_path = flash_files[offset_str]
        full_path = build_dir / rel_path

        if not full_path.exists():
            # Try alternative locations
            alt_path = build_dir.parent / rel_path
            if alt_path.exists():
                full_path = alt_path
            else:
                print(f"  WARNING: {rel_path} not found, skipping", file=sys.stderr)
                continue

        size = full_path.stat().st_size
        sha = sha256_file(full_path)

        name = name_map.get(offset_str, os.path.splitext(os.path.basename(rel_path))[0])
        art = {
            "name": name,
            "path": str(full_path.relative_to(build_dir.parent)),
            "offset": offset_str,
            "size": size,
            "sha256": sha,
        }
        artifacts.append(art)
        print(f"  {name}: offset={offset_str} size={size} sha256={sha[:16]}...", file=sys.stderr)

    # Read sdkconfig for marker
    sdkconfig = build_dir.parent / "sdkconfig"
    sdkconfig_marker = extract_sdkconfig_marker(sdkconfig)

    # Use the same sdkconfig_marker from sdkconfig.defaults as fallback
    if not sdkconfig_marker:
        sdkconfig_defaults = build_dir.parent / "sdkconfig.defaults"
        if sdkconfig_defaults.exists():
            sdkconfig_marker = detect_marker(
                sdkconfig_defaults.read_text(errors="replace"),
                "CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL"
            )

    # Build manifest
    manifest = {
        "manifest_version": "1.0.0",
        "code_id": "R7C",
        "phase": "P4-R1C",
        "profile": "safe-hid-only",
        "build_dir": build_dir.name,
        "sdkconfig_marker": sdkconfig_marker,
        "usb_identity": {
            "vid": "0x303A",
            "pid": "0x4014",
            "product": "BOOTMUX Keyboard Safe",
            "serial": "BOOTMUX-HID-SAFE",
            "device_class": "0x00",
            "device_subclass": "0x00",
            "device_protocol": "0x00"
        },
        "flash_params": {
            "flash_mode": flash_settings.get("flash_mode", "dio"),
            "flash_freq": flash_settings.get("flash_freq", "80m"),
            "flash_size": flash_settings.get("flash_size", "2MB"),
        },
        "artifacts": artifacts,
        "forbidden_strings": [
            "CDC_ECM", "CDC_NCM", "RNDIS", "rndis",
            "usb_network", "USB_NETIF", "tinyusb_net", "tusb_net",
            "dhcps_start", "dhcp_server_start",
            "napt_enable", "ip_forward_enable",
            "BOOTMUX Bridge Experimental", "BOOTMUX-R7A-NCM"
        ],
        "required_strings": [
            "BOOTMUX Keyboard Safe",
            "BOOTMUX-HID-SAFE",
            "BOOTMUX_USB_NETWORK_SAFE_OFF"
        ]
    }

    # Write manifest
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"\nManifest written to {output_path}", file=sys.stderr)
    print(f"  build_dir={build_dir.name}", file=sys.stderr)
    print(f"  artifacts={len(artifacts)}", file=sys.stderr)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate safe-flash-manifest.json")
    parser.add_argument("build_dir", type=str, help="Build directory path")
    parser.add_argument("--output", type=str, default=None,
                        help="Output manifest path (default: <build_dir>/../safe-flash-manifest.json)")
    args = parser.parse_args()

    build_dir = Path(args.build_dir).resolve()
    if not build_dir.is_dir():
        print(f"ERROR: build dir not found: {build_dir}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else (
        build_dir.parent / "safe-flash-manifest.json"
    )

    generate_manifest(build_dir, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
