#!/bin/sh
set -eu

TRANSCRIPT=${1:-"$HOME/.bootmux/hid-transcript"}
MAX_BYTES=${BOOTMUX_HID_TRANSCRIPT_MAX_BYTES:-131072}
mkdir -p "$(dirname "$TRANSCRIPT")"
umask 077
: > "$TRANSCRIPT"
chmod 600 "$TRANSCRIPT"

trim_transcript() {
    size=$(wc -c < "$TRANSCRIPT")
    if [ "$size" -gt "$MAX_BYTES" ]; then
        tail -c "$MAX_BYTES" "$TRANSCRIPT" > "$TRANSCRIPT.tmp"
        chmod 600 "$TRANSCRIPT.tmp"
        mv "$TRANSCRIPT.tmp" "$TRANSCRIPT"
    fi
}

cleanup() {
    if [ -n "${TRIM_PID:-}" ]; then
        kill "$TRIM_PID" 2>/dev/null || true
        wait "$TRIM_PID" 2>/dev/null || true
    fi
    : > "$TRANSCRIPT"
    rm -f "$TRANSCRIPT"
}
trap cleanup EXIT HUP INT TERM

(
    while :; do
        trim_transcript
        sleep 0.1
    done
) &
TRIM_PID=$!

TERM=dumb NO_COLOR=1 script -q -f -c 'env TERM=dumb NO_COLOR=1 /bin/bash --noprofile --norc -i' "$TRANSCRIPT"
