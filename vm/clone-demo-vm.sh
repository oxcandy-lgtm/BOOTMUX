#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo "VM_PROVIDER_UNAVAILABLE" >&2; exit 78; }
limactl list --format '{{.Name}}' | grep -qx 'bootmux-clean' || { echo "CLEAN_VM_REQUIRED" >&2; exit 65; }
if limactl list --format '{{.Name}}' | grep -qx 'bootmux-demo'; then exit 0; fi
echo "LIMA_CLONE_UNAVAILABLE: regenerate demo from clean baseline" >&2
exit 69
