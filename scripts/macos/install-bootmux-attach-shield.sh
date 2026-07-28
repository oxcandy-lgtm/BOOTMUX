#!/bin/bash
# R7C P4-R0B — Install BOOTMUX Mac Pre-Attach Shield LaunchDaemon (Ephemeral).
# Requires sudo.  Does NOT arm the shield — run --arm separately after install.
set -euo pipefail

LABEL="com.bootmux.attach-shield"
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/launchd/${LABEL}.plist"
PLIST_DST="/Library/LaunchDaemons/${LABEL}.plist"
SHIELD_SRC="$(cd "$(dirname "$0")" && pwd)/bootmux-attach-shield.py"
INSTALL_DIR="/usr/local/bootmux/scripts/macos"
SHIELD="${INSTALL_DIR}/bootmux-attach-shield.py"
STATE_DIR="/var/db/bootmux-shield"

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: must run as root (sudo)" >&2
    exit 1
fi

echo "=== BOOTMUX Attach Shield Installer (Ephemeral Edition) ==="

# 1. Validate shield script exists
if [[ ! -f "$SHIELD_SRC" ]]; then
    echo "ERROR: shield script not found: $SHIELD_SRC" >&2
    exit 1
fi

# 2. Validate plist
if ! plutil -lint "$PLIST_SRC" >/dev/null 2>&1; then
    echo "ERROR: invalid plist: $PLIST_SRC" >&2
    exit 1
fi

# 3. Install shield to stable path (plist references /usr/local/bootmux/...)
mkdir -p "$INSTALL_DIR"
cp "$SHIELD_SRC" "$SHIELD"
chmod 0755 "$SHIELD"
echo "shield_installed=$SHIELD"

# 4. Create state directory (root-owned, 0700)
mkdir -p "$STATE_DIR"
chmod 0700 "$STATE_DIR"
chown root:wheel "$STATE_DIR"
echo "state_dir=$STATE_DIR (0700 root:wheel)"

# 5. Unload existing daemon if present
if launchctl list "$LABEL" >/dev/null 2>&1; then
    echo "unloading existing daemon..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# 6. Install plist
cp "$PLIST_SRC" "$PLIST_DST"
chmod 0644 "$PLIST_DST"
chown root:wheel "$PLIST_DST"
echo "plist_installed=$PLIST_DST"

# 7. Load daemon (does not arm — daemon checks state file)
launchctl load "$PLIST_DST"
echo "daemon_loaded=$LABEL"

# 8. Verify
if launchctl list "$LABEL" >/dev/null 2>&1; then
    echo "INSTALL=OK"
else
    echo "INSTALL=FAILED (daemon not loaded)" >&2
    exit 1
fi

echo ""
echo "Next: sudo python3 $SHIELD --arm --ttl 1800"
