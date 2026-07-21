#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo "VM_PROVIDER_UNAVAILABLE" >&2; exit 78; }
INSTANCE=${1:-bootmux-clean}
limactl shell "$INSTANCE" -- sh -lc '
  set -eu
  case "$(uname -m)" in aarch64|arm64) ;; *) echo ARM64_REQUIRED >&2; exit 65;; esac
  if command -v codex >/dev/null 2>&1; then echo CODEX_ABSENT_REQUIRED >&2; exit 66; fi
  echo ARCHITECTURE_ARM64_PASS
  echo CODEX_ABSENT_PASS
'
