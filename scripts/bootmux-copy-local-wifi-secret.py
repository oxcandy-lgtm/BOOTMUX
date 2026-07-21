#!/usr/bin/env python3
"""Copy one local BOOTMUX Wi-Fi field without printing its value."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


SECRET_PATH = Path.home() / ".config" / "bootmux" / "secrets" / "wifi.env"
FIELDS = {
    "ssid": "BOOTMUX_WIFI_SSID",
    "password": "BOOTMUX_WIFI_PASSWORD",
}


def fail(message: str) -> "NoReturn":
    print(message, file=sys.stderr)
    raise SystemExit(1)


def read_field(field: str) -> str:
    path = SECRET_PATH
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        fail("LOCAL_SECRET_FILE: UNAVAILABLE")
    if mode != 0o600:
        fail("LOCAL_SECRET_FILE_PERMISSIONS: FAIL")

    values: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or key not in FIELDS.values() or not value:
                fail("LOCAL_SECRET_FORMAT: FAIL")
            values[key] = value
    except (OSError, UnicodeError):
        fail("LOCAL_SECRET_FILE: UNREADABLE")

    if set(values) != set(FIELDS.values()):
        fail("LOCAL_SECRET_KEYS: FAIL")
    return values[FIELDS[field]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("field", choices=sorted(FIELDS))
    args = parser.parse_args()

    value = read_field(args.field)
    try:
        subprocess.run(
            ["pbcopy"],
            input=value.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
    except (OSError, subprocess.CalledProcessError):
        fail("CLIPBOARD_COPY: FAIL")

    print(f"COPIED_{args.field.upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
