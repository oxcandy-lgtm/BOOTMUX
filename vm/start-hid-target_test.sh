#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DIR=$(mktemp -d "${TMPDIR:-/tmp}/bootmux-hid-target-test.XXXXXX")
TRANSCRIPT="$DIR/transcript"
trap 'rm -f "$DIR/stdout" "$DIR/stderr"; rmdir "$DIR" 2>/dev/null || true' EXIT HUP INT TERM

set +e
BOOTMUX_HID_TRANSCRIPT_MAX_BYTES=64 \
BOOTMUX_HID_TARGET_COMMAND='while :; do printf 0123456789; done' \
    "$ROOT/start-hid-target.sh" "$TRANSCRIPT" >"$DIR/stdout" 2>"$DIR/stderr"
status=$?
set -e

[ "$status" -eq 75 ]
grep -q '^HID_TARGET_TRANSCRIPT_LIMIT_EXCEEDED$' "$DIR/stderr"
[ ! -e "$TRANSCRIPT" ]
echo HID_TARGET_THRESHOLD_TEST=PASS
