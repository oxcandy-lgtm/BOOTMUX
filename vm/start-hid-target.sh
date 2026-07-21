#!/bin/sh
set -eu

TRANSCRIPT=${1:-"$HOME/.bootmux/hid-transcript"}
MAX_BYTES=${BOOTMUX_HID_TRANSCRIPT_MAX_BYTES:-131072}
HID_COMMAND=${BOOTMUX_HID_TARGET_COMMAND:-'env TERM=dumb NO_COLOR=1 /bin/bash --noprofile --norc -i'}
mkdir -p "$(dirname "$TRANSCRIPT")"
umask 077
: > "$TRANSCRIPT"
chmod 600 "$TRANSCRIPT"

cleanup() {
    if [ -n "${SCRIPT_PID:-}" ]; then
        kill "$SCRIPT_PID" 2>/dev/null || true
        wait "$SCRIPT_PID" 2>/dev/null || true
    fi
    : > "$TRANSCRIPT"
    rm -f "$TRANSCRIPT"
}
trap cleanup EXIT HUP INT TERM

case "$MAX_BYTES" in
    ''|*[!0-9]*) echo HID_TARGET_INVALID_MAX_BYTES >&2; exit 64 ;;
esac
[ "$MAX_BYTES" -gt 0 ] || { echo HID_TARGET_INVALID_MAX_BYTES >&2; exit 64; }

# The writer is never unlinked or replaced while script owns the descriptor.
# Crossing the bound terminates the writer explicitly and is visible to the
# caller; this is fail-closed rather than silent truncation.
if script --version 2>&1 | grep -qi util-linux; then
    script -q -f -c "$HID_COMMAND" "$TRANSCRIPT" &
else
    script -q "$TRANSCRIPT" /bin/sh -c "$HID_COMMAND" &
fi
SCRIPT_PID=$!
status=0
while kill -0 "$SCRIPT_PID" 2>/dev/null; do
    size=$(wc -c < "$TRANSCRIPT")
    if [ "$size" -ge "$MAX_BYTES" ]; then
        echo HID_TARGET_TRANSCRIPT_LIMIT_EXCEEDED >&2
        kill -TERM "$SCRIPT_PID" 2>/dev/null || true
        status=75
        break
    fi
    sleep 0.05
done
script_status=0
wait "$SCRIPT_PID" 2>/dev/null || script_status=$?
SCRIPT_PID=
if [ "$status" -ne 0 ]; then
    exit "$status"
fi
exit "$script_status"
