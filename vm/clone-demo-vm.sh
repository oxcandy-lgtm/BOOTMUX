#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo "VM_PROVIDER_UNAVAILABLE" >&2; exit 78; }
limactl list --format '{{.Name}}' | grep -qx 'bootmux-clean' || { echo "CLEAN_VM_REQUIRED" >&2; exit 65; }
if limactl list --quiet | grep -qx 'bootmux-demo'; then
  limactl start bootmux-demo
  exit 0
fi
if limactl list --format '{{.Name}} {{.Status}}' | grep -q '^bootmux-clean Running$'; then
  limactl stop bootmux-clean
fi
limactl clone bootmux-clean bootmux-demo --start
