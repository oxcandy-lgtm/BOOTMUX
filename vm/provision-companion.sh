#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo "VM_PROVIDER_UNAVAILABLE" >&2; exit 78; }
INSTANCE=${1:-bootmux-demo}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
limactl shell "$INSTANCE" -- mkdir -p /tmp/bootmux-source
tar -C "$ROOT" --exclude .git --exclude .tools --exclude .pio -cf - companion | limactl shell "$INSTANCE" -- tar -C /tmp/bootmux-source -xf -
tar -C "$ROOT" -cf - vm | limactl shell "$INSTANCE" -- tar -C /tmp/bootmux-source -xf -
limactl shell "$INSTANCE" -- sh -lc 'set -eu; command -v go >/dev/null; command -v node >/dev/null; command -v npm >/dev/null; mkdir -p "$HOME/bin" "$HOME/bootmux"; cp /tmp/bootmux-source/vm/install-codex.sh "$HOME/bootmux/"; cp /tmp/bootmux-source/vm/run-codex-prompt.sh "$HOME/bootmux/"; chmod +x "$HOME/bootmux"/*.sh; cd /tmp/bootmux-source/companion; go version; go test ./...; go test -race ./...; go vet ./...; go build -trimpath -o "$HOME/bin/bootmux-companion" .'
