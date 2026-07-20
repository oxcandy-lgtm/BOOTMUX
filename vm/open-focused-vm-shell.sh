#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo VM_PROVIDER_UNAVAILABLE >&2; exit 78; }
osascript -e 'tell application "Terminal" to activate' -e 'tell application "Terminal" to do script "limactl shell bootmux-demo -- bash -l"'
