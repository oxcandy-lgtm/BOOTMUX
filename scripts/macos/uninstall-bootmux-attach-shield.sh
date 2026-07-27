#!/bin/bash
# R7C P4-R0 — Uninstall BOOTMUX Mac Pre-Attach Shield.
# Disarms first (if armed), removes PF anchor, unloads daemon, removes plist.
# Preserves state directory for forensic review.
set -euo pipefail

LABEL="com.bootmux.attach-shield"
PLIST_DST="/Library/LaunchDaemons/${LABEL}.plist"
SHIELD="$(cd "$(dirname "$0")" && pwd)/bootmux-attach-shield.py"
PF_ANCHOR="com.bootmux.attach-shield"
STATE_DIR="/var/db/bootmux-shield"

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: must run as root (sudo)" >&2
    exit 1
fi

echo "=== BOOTMUX Attach Shield Uninstaller ==="

# 1. Disarm if armed (removes pinned routes, PF anchor)
if [[ -f "$SHIELD" ]]; then
    python3 "$SHIELD" --disarm 2>/dev/null || true
fi

# 2. Remove PF anchor (only our rules)
pfctl -a "$PF_ANCHOR" -F all 2>/dev/null || true
echo "pf_anchor_cleared=$PF_ANCHOR"

# 3. Unload daemon
if launchctl list "$LABEL" >/dev/null 2>&1; then
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    echo "daemon_unloaded=$LABEL"
fi

# 4. Remove plist
if [[ -f "$PLIST_DST" ]]; then
    rm -f "$PLIST_DST"
    echo "plist_removed=$PLIST_DST"
fi

# 5. Preserve state directory for forensics (do NOT delete)
if [[ -d "$STATE_DIR" ]]; then
    echo "state_preserved=$STATE_DIR (not deleted — forensic evidence)"
fi

echo "UNINSTALL=OK"
