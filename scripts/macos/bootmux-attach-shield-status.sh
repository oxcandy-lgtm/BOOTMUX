#!/bin/bash
# R7C P4-R0 — BOOTMUX Attach Shield status (read-only, no sudo required).
set -euo pipefail

LABEL="com.bootmux.attach-shield"
SHIELD="$(cd "$(dirname "$0")" && pwd)/bootmux-attach-shield.py"
PLIST_DST="/Library/LaunchDaemons/${LABEL}.plist"
STATE_DIR="/var/db/bootmux-shield"

echo "=== BOOTMUX Attach Shield Status ==="

# Daemon status
if launchctl list "$LABEL" >/dev/null 2>&1; then
    echo "daemon=LOADED"
else
    echo "daemon=NOT_LOADED"
fi

# Plist installed
if [[ -f "$PLIST_DST" ]]; then
    echo "plist=INSTALLED"
else
    echo "plist=NOT_INSTALLED"
fi

# State directory
if [[ -d "$STATE_DIR" ]]; then
    echo "state_dir=EXISTS"
    if [[ -f "$STATE_DIR/shield-state.json" ]]; then
        echo "state_file=EXISTS"
    else
        echo "state_file=ABSENT"
    fi
else
    echo "state_dir=ABSENT"
fi

# Shield status (read-only)
if [[ -f "$SHIELD" ]]; then
    echo "---"
    python3 "$SHIELD" --status 2>/dev/null || echo "shield_status=UNAVAILABLE"
fi
