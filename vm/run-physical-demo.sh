#!/bin/sh
set -eu

# Bounded physical-demo harness. It owns only the child processes started below.
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
INSTANCE=${BOOTMUX_LIMA_INSTANCE:-bootmux-demo}
COMPANION_PORT=${BOOTMUX_COMPANION_PORT:-8765}
FORWARD_PORT=${BOOTMUX_FORWARD_PORT:-18765}
VM_TRANSCRIPT=${BOOTMUX_HID_TRANSCRIPT:-"$HOME/.bootmux/hid-transcript"}
WAIT_SECONDS=${BOOTMUX_DEMO_WAIT_SECONDS:-20}
COMPANION_PID=
FORWARDER_PID=
VM_STARTED=0

fail() {
    echo "BOOTMUX_PHYSICAL_DEMO_FAILED stage=$1" >&2
    exit 1
}

cleanup() {
    if [ -n "${FORWARDER_PID:-}" ]; then
        kill "$FORWARDER_PID" 2>/dev/null || true
        wait "$FORWARDER_PID" 2>/dev/null || true
    fi
    if [ -n "${COMPANION_PID:-}" ]; then
        kill "$COMPANION_PID" 2>/dev/null || true
        wait "$COMPANION_PID" 2>/dev/null || true
    fi
    if [ "$VM_STARTED" -eq 1 ]; then
        "$LIMA" stop "$INSTANCE" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT HUP INT TERM

LIMA=${LIMA_BIN:-limactl}
command -v "$LIMA" >/dev/null 2>&1 || fail VM
command -v curl >/dev/null 2>&1 || fail JUDGE
command -v python3 >/dev/null 2>&1 || fail FORWARDER
[ -x "$ROOT/tools/bootmux_tcp_forward.py" ] || fail FORWARDER
[ -x "$ROOT/vm/start-hid-target.sh" ] || fail HID_TARGET

STATUS=$($LIMA list --format '{{.Name}} {{.Status}}' 2>/dev/null | awk -v name="$INSTANCE" '$1 == name { print $2; exit }' || true)
if [ "$STATUS" = "Stopped" ] || [ -z "$STATUS" ]; then
    if [ -z "$STATUS" ]; then
        fail VM
    fi
    "$LIMA" start "$INSTANCE" >/dev/null
    VM_STARTED=1
fi

VM_COMPANION=$($LIMA shell "$INSTANCE" -- sh -lc 'test -x "$HOME/bin/bootmux-companion" && printf PASS' 2>/dev/null || true)
[ "$VM_COMPANION" = PASS ] || fail COMPANION

# The VM-side process is tied to this limactl shell child and is killed in cleanup.
"$LIMA" shell "$INSTANCE" -- sh -lc \
    'exec "$HOME/bin/bootmux-companion" -addr 127.0.0.1:'"$COMPANION_PORT"' -mirror-path '"$(printf '%s' "$VM_TRANSCRIPT" | sed "s/'/'\\''/g")"' -shell /bin/bash' \
    >/dev/null 2>&1 &
COMPANION_PID=$!

ready=0
i=0
while [ "$i" -lt "$WAIT_SECONDS" ]; do
    if "$LIMA" shell "$INSTANCE" -- sh -lc 'curl -fsS http://127.0.0.1:'"$COMPANION_PORT"'/judge >/dev/null' 2>/dev/null; then
        ready=1
        break
    fi
    i=$((i + 1))
    sleep 1
done
[ "$ready" -eq 1 ] || fail COMPANION

python3 "$ROOT/tools/bootmux_tcp_forward.py" \
    --listen "${BOOTMUX_LISTEN_HOST:-0.0.0.0}:$FORWARD_PORT" \
    --target "127.0.0.1:$COMPANION_PORT" \
    >/dev/null 2>&1 &
FORWARDER_PID=$!
i=0
while [ "$i" -lt "$WAIT_SECONDS" ]; do
    kill -0 "$FORWARDER_PID" 2>/dev/null && break
    i=$((i + 1))
    sleep 1
done
kill -0 "$FORWARDER_PID" 2>/dev/null || fail FORWARDER

LAN_IP=$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}' | xargs -I{} ifconfig {} 2>/dev/null | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}' || true)
[ -n "$LAN_IP" ] || LAN_IP=LOCAL_INTERFACE_ADDRESS

echo BOOTMUX_PHYSICAL_DEMO_READY
echo "VM           PASS"
echo "COMPANION    PASS"
echo "FORWARDER    PASS"
echo "HID_TARGET   READY (run vm/start-hid-target.sh in the focused Terminal)"
echo "JUDGE        READY (http://127.0.0.1:$COMPANION_PORT/judge)"
echo "IPHONE_WS    READY (ws://$LAN_IP:$FORWARD_PORT/v1/terminal)"
echo "Press Ctrl-C to stop only launcher-owned processes."
wait "$FORWARDER_PID"
