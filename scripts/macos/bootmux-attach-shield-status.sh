#!/bin/bash
# R7C P4-R0B — BOOTMUX Attach Shield status (read-only, no sudo required).
set -euo pipefail

SHIELD="/usr/local/bootmux/scripts/macos/bootmux-attach-shield.py"
LABEL="com.bootmux.attach-shield"
PLIST="/Library/LaunchDaemons/${LABEL}.plist"
STATE_DIR="/var/db/bootmux-shield"

echo "=== BOOTMUX Attach Shield Status (Ephemeral Edition) ==="

# Daemon
if launchctl list "$LABEL" >/dev/null 2>&1; then
    echo "daemon=LOADED"
else
    echo "daemon=NOT_LOADED"
fi

# Plist
if [[ -f "$PLIST" ]]; then
    echo "plist=INSTALLED"
else
    echo "plist=ABSENT"
fi

# State dir
if [[ -d "$STATE_DIR" ]]; then
    echo "state_dir=EXISTS"
else
    echo "state_dir=ABSENT"
fi

# Shield script
if [[ -f "$SHIELD" ]]; then
    echo "shield_script=INSTALLED"
    # Run shield --status for detailed state
    python3 "$SHIELD" --status 2>/dev/null || echo "shield_status=UNAVAILABLE"
else
    echo "shield_script=ABSENT"
    echo "STATUS=NOT_INSTALLED"
fi
