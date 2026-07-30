#!/bin/bash
#
# install-bootmux-network-guardian.sh — R7C P2
#
# Idempotently installs the BOOTMUX macOS network guardian LaunchDaemon.
#   * root-only
#   * copies the guardian script + plist into stable system locations
#   * creates a hardened state directory (0700 root:wheel)
#   * loads the daemon
#
# Re-running is safe: it overwrites only guardian-owned files and never
# touches unrelated files.

set -euo pipefail

LABEL="com.bootmux.network-guardian"
PLIST_NAME="${LABEL}.plist"
INSTALL_ROOT="/Library/Application Support/BOOTMUX/network-guardian"
INSTALL_SCRIPT="${INSTALL_ROOT}/bootmux-network-guardian.py"
DAEMON_PLIST="/Library/LaunchDaemons/${PLIST_NAME}"
STATE_DIR="/var/db/bootmux-network-guardian"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_SCRIPT="${SCRIPT_DIR}/bootmux-network-guardian.py"
SRC_PLIST="${SCRIPT_DIR}/launchd/${PLIST_NAME}"

log() { printf '[install] %s\n' "$*"; }
die() { printf '[install] ERROR: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "must run as root (use sudo)"
[[ -f "$SRC_SCRIPT" ]] || die "missing source script: $SRC_SCRIPT"
[[ -f "$SRC_PLIST" ]] || die "missing source plist: $SRC_PLIST"

# 1. Install the guardian script.
log "installing guardian script -> ${INSTALL_SCRIPT}"
mkdir -p "$INSTALL_ROOT"
install -m 0755 -o root -g wheel "$SRC_SCRIPT" "$INSTALL_SCRIPT"

# 2. Install the LaunchDaemon plist.
log "installing LaunchDaemon plist -> ${DAEMON_PLIST}"
install -m 0644 -o root -g wheel "$SRC_PLIST" "$DAEMON_PLIST"

# 3. Validate the plist before loading.
if ! plutil -lint "$DAEMON_PLIST" >/dev/null; then
  die "installed plist failed plutil -lint"
fi

# 4. Create the hardened state directory (fail-closed permissions).
log "ensuring state dir ${STATE_DIR} (0700 root:wheel)"
mkdir -p "$STATE_DIR"
chmod 0700 "$STATE_DIR"
chown root:wheel "$STATE_DIR"

# 5. (Re)load the daemon idempotently.
if launchctl print "system/${LABEL}" >/dev/null 2>&1; then
  log "unloading existing daemon"
  launchctl bootout "system/${LABEL}" >/dev/null 2>&1 || true
fi
log "loading daemon"
launchctl bootstrap system "$DAEMON_PLIST"

log "done. status: launchctl print system/${LABEL}"
