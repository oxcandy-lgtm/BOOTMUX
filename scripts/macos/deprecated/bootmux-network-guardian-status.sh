#!/bin/bash
#
# bootmux-network-guardian-status.sh — R7C P2
#
# Read-only status probe. Delegates to the guardian's --status command, which
# emits a sanitized (SSID-redacted) machine + human report. Never mutates.
#
# Works whether or not the daemon is installed: it locates the guardian script
# in the installed location first, then falls back to the repo copy.

set -euo pipefail

LABEL="com.bootmux.network-guardian"
INSTALL_SCRIPT="/Library/Application Support/BOOTMUX/network-guardian/bootmux-network-guardian.py"
STATE_DIR="/var/db/bootmux-network-guardian"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_SCRIPT="${SCRIPT_DIR}/bootmux-network-guardian.py"

# Pick the guardian script.
GUARDIAN=""
if [[ -f "$INSTALL_SCRIPT" ]]; then
  GUARDIAN="$INSTALL_SCRIPT"
elif [[ -f "$REPO_SCRIPT" ]]; then
  GUARDIAN="$REPO_SCRIPT"
else
  printf '[status] ERROR: guardian script not found\n' >&2
  exit 1
fi

# Daemon load state (informational).
if launchctl print "system/${LABEL}" >/dev/null 2>&1; then
  printf '[status] daemon: loaded (system/%s)\n' "$LABEL"
else
  printf '[status] daemon: not loaded\n'
fi

# Delegate to the guardian's sanitized status reporter.
exec /usr/bin/python3 "$GUARDIAN" --status --state-dir "$STATE_DIR"
