#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
"$ROOT/create-clean-vm.sh"
"$ROOT/verify-clean-state.sh" bootmux-clean
"$ROOT/clone-demo-vm.sh"
"$ROOT/verify-network.sh" bootmux-demo
"$ROOT/provision-companion.sh" bootmux-demo
echo VM_READY
