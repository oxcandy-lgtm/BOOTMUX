#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$ROOT/tools/bootmux_tcp_forward.py" --listen 0.0.0.0:18765 --target 127.0.0.1:8765
