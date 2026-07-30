#!/bin/bash
#
# uninstall-bootmux-network-guardian.sh — R7C P2
#
# Idempotently removes the BOOTMUX macOS network guardian LaunchDaemon.
#   * root-only
#   * unloads the daemon
#   * removes ONLY guardian-owned files (plist, installed script)
#   * preserves state evidence by default; --purge removes it outright
#
# Unrelated files are never touched.

set -euo pipefail

LABEL="com.bootmux.network-guardian"
PLIST_NAME="${LABEL}.plist"
INSTALL_ROOT="/Library/Application Support/BOOTMUX/network-guardian"
DAEMON_PLIST="/Library/LaunchDaemons/${PLIST_NAME}"
STATE_DIR="/var/db/bootmux-network-guardian"
EVIDENCE_DIR="/var/db/bootmux-network-guardian.evidence.$(date +%Y%m%d%H%M%S)"

PURGE=0
for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=1 ;;
    *) printf 'unknown arg: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

log() { printf '[uninstall] %s\n' "$*"; }
die() { printf '[uninstall] ERROR: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "must run as root (use sudo)"

# 1. Unload the daemon (idempotent).
if launchctl print "system/${LABEL}" >/dev/null 2>&1; then
  log "unloading daemon"
  launchctl bootout "system/${LABEL}" >/dev/null 2>&1 || true
else
  log "daemon not loaded; nothing to unload"
fi

# 2. Remove guardian-owned launch files.
if [[ -f "$DAEMON_PLIST" ]]; then
  log "removing ${DAEMON_PLIST}"
  rm -f "$DAEMON_PLIST"
fi
if [[ -d "$INSTALL_ROOT" ]]; then
  log "removing ${INSTALL_ROOT}"
  rm -rf "$INSTALL_ROOT"
fi

# 3. Handle state directory.
if [[ -d "$STATE_DIR" ]]; then
  if [[ $PURGE -eq 1 ]]; then
    log "purging state dir ${STATE_DIR}"
    rm -rf "$STATE_DIR"
  else
    log "preserving state evidence -> ${EVIDENCE_DIR}"
    mv "$STATE_DIR" "$EVIDENCE_DIR"
    chmod 0700 "$EVIDENCE_DIR"
  fi
else
  log "no state dir present"
fi

log "done."
