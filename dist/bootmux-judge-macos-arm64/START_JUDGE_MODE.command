#!/bin/sh
set -eu
BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
echo "BOOTMUX Judge Mode: http://127.0.0.1:8765/judge"
echo "Press Ctrl-C to stop the local Companion."
open "http://127.0.0.1:8765/judge" 2>/dev/null || true
exec "$BASE_DIR/bootmux-companion" -addr 127.0.0.1:8765
