#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo "VM_PROVIDER_UNAVAILABLE" >&2; exit 78; }
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! limactl list --quiet | grep -qx 'bootmux-clean'; then
  limactl create -y --name bootmux-clean "$ROOT/bootmux-lima.yaml"
fi
limactl start bootmux-clean
