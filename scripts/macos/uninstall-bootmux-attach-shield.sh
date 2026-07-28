#!/bin/bash
# R7C P4-R0B — Uninstall BOOTMUX Mac Pre-Attach Shield.
# Supports --purge (complete removal) and --keep-evidence PATH (archive report).
set -euo pipefail

LABEL="com.bootmux.attach-shield"
SHIELD="/usr/local/bootmux/scripts/macos/bootmux-attach-shield.py"
PLIST="/Library/LaunchDaemons/${LABEL}.plist"
STATE_DIR="/var/db/bootmux-shield"
PURGE=false
EVIDENCE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge) PURGE=true; shift ;;
        --keep-evidence) EVIDENCE="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: must run as root (sudo)" >&2
    exit 1
fi

echo "=== BOOTMUX Attach Shield Uninstaller (Ephemeral Edition) ==="

# Delegate to shield script for session close + artifact removal
if [[ -f "$SHIELD" ]]; then
    if $PURGE; then
        python3 "$SHIELD" --uninstall --purge
    elif [[ -n "$EVIDENCE" ]]; then
        python3 "$SHIELD" --uninstall --keep-evidence "$EVIDENCE"
    else
        python3 "$SHIELD" --uninstall --purge
    fi
else
    # Fallback: manual cleanup if shield script missing
    echo "shield_script=MISSING (manual cleanup)"
    launchctl unload "$PLIST" 2>/dev/null || true
    pfctl -a "$LABEL" -F all 2>/dev/null || true
    rm -f "$PLIST"
    if $PURGE; then
        rm -rf "$STATE_DIR"
    fi
    echo "UNINSTALL=MANUAL_OK"
fi
