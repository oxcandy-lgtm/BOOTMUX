#!/bin/sh
set -eu
BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SERVER_LOG=${TMPDIR:-/tmp}/bootmux-judge-$$.log
SERVER_PID=""
cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$SERVER_LOG"
}
trap cleanup INT TERM EXIT
"$BASE_DIR/bootmux-companion" -addr 127.0.0.1:8765 >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!
READY=0
i=0
while [ "$i" -lt 50 ]; do
    if curl -fsS http://127.0.0.1:8765/judge >/dev/null 2>&1; then READY=1; break; fi
    i=$((i + 1)); sleep 0.1
done
if [ "$READY" -ne 1 ]; then
    echo "BOOTMUX Judge Mode failed to start on loopback port 8765." >&2
    tail -n 5 "$SERVER_LOG" >&2 || true
    exit 1
fi
echo "BOOTMUX Judge Mode: http://127.0.0.1:8765/judge"
echo "Press Ctrl-C to stop the local Companion."
open "http://127.0.0.1:8765/judge" 2>/dev/null || true
set +e
while kill -0 "$SERVER_PID" 2>/dev/null; do
    sleep 0.1
done
wait "$SERVER_PID"
EXIT_CODE=$?
set -e
exit "$EXIT_CODE"
