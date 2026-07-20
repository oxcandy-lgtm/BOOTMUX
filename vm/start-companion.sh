#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo VM_PROVIDER_UNAVAILABLE >&2; exit 78; }
INSTANCE=${1:-bootmux-demo}
limactl shell "$INSTANCE" -- sh -lc 'exec "$HOME/bin/bootmux-companion" -addr 127.0.0.1:8765'
