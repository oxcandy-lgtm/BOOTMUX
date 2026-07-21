#!/bin/sh
set -eu

# Bounded physical-demo harness. It owns only the child processes started below.
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
INSTANCE=${BOOTMUX_LIMA_INSTANCE:-bootmux-demo}
COMPANION_PORT=${BOOTMUX_COMPANION_PORT:-8765}
FORWARD_PORT=${BOOTMUX_FORWARD_PORT:-18765}
VM_TRANSCRIPT_RELATIVE=${BOOTMUX_HID_TRANSCRIPT_RELATIVE:-.bootmux/hid-transcript}
WAIT_SECONDS=${BOOTMUX_DEMO_WAIT_SECONDS:-20}
COMPANION_PID=
FORWARDER_PID=
VM_STARTED=0

fail() {
    echo "BOOTMUX_PHYSICAL_DEMO_FAILED stage=$1 reason=$2" >&2
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
case "$LIMA" in
    */*) [ -x "$LIMA" ] || fail VM LIMA_COMMAND_UNAVAILABLE ;;
    *) command -v "$LIMA" >/dev/null 2>&1 || fail VM LIMA_COMMAND_UNAVAILABLE ;;
esac
command -v curl >/dev/null 2>&1 || fail JUDGE CURL_COMMAND_UNAVAILABLE
command -v python3 >/dev/null 2>&1 || fail FORWARDER PYTHON_COMMAND_UNAVAILABLE
[ -x "$ROOT/tools/bootmux_tcp_forward.py" ] || fail FORWARDER FORWARDER_NOT_FOUND

case "$VM_TRANSCRIPT_RELATIVE" in
    /*|*..*|*[!A-Za-z0-9._/-]*) fail HID_TARGET INVALID_VM_TRANSCRIPT_PATH ;;
esac

STATUS=$($LIMA list --format '{{.Name}} {{.Status}}' 2>/dev/null | awk -v name="$INSTANCE" '$1 == name { print $2; exit }' || true)
if [ -z "$STATUS" ]; then
    fail VM INSTANCE_NOT_FOUND
fi
if [ "$STATUS" = "Stopped" ]; then
    "$LIMA" start "$INSTANCE" >/dev/null
    VM_STARTED=1
fi

VM_COMPANION=$($LIMA shell "$INSTANCE" -- sh -lc 'test -x "$HOME/bin/bootmux-companion" && printf PASS' 2>/dev/null || true)
[ "$VM_COMPANION" = PASS ] || fail COMPANION PROVISIONED_COMPANION_NOT_FOUND
VM_HID_TARGET=$($LIMA shell "$INSTANCE" -- sh -lc 'test -x /tmp/bootmux-source/vm/start-hid-target.sh && printf PASS' 2>/dev/null || true)
[ "$VM_HID_TARGET" = PASS ] || fail HID_TARGET PROVISIONED_TARGET_SCRIPT_NOT_FOUND

# Resolve and create the canonical path inside the VM; host HOME is never expanded.
$LIMA shell "$INSTANCE" -- sh -lc 'set -eu; rel=$1; path="$HOME/$rel"; mkdir -p "$(dirname "$path")"; : > "$path"; chmod 600 "$path"' sh "$VM_TRANSCRIPT_RELATIVE" || fail HID_TARGET VM_TRANSCRIPT_INIT_FAILED

# The VM-side process is tied to this limactl shell child and is killed in cleanup.
"$LIMA" shell "$INSTANCE" -- sh -lc \
    'set -eu; rel=$1; exec "$HOME/bin/bootmux-companion" -addr 127.0.0.1:'"$COMPANION_PORT"' -mirror-path "$HOME/$rel" -shell /bin/bash' \
    sh "$VM_TRANSCRIPT_RELATIVE" \
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
[ "$ready" -eq 1 ] || fail COMPANION COMPANION_NOT_READY

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
kill -0 "$FORWARDER_PID" 2>/dev/null || fail FORWARDER FORWARDER_NOT_READY

LAN_IP=$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}' | xargs -I{} ifconfig {} 2>/dev/null | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}' || true)
[ -n "$LAN_IP" ] || LAN_IP=LOCAL_INTERFACE_ADDRESS

echo BOOTMUX_PHYSICAL_DEMO_READY
echo "VM           PASS"
echo "COMPANION    PASS"
echo "FORWARDER    PASS"
printf 'HID_TARGET   READY (run: limactl shell %s -- sh -lc '\''exec /tmp/bootmux-source/vm/start-hid-target.sh "\$HOME/%s"'\'')\n' "$INSTANCE" "$VM_TRANSCRIPT_RELATIVE"
echo "JUDGE        READY (http://127.0.0.1:$COMPANION_PORT/judge)"
echo "IPHONE_WS    READY (ws://$LAN_IP:$FORWARD_PORT/v1/terminal)"
echo "Press Ctrl-C to stop only launcher-owned processes."
wait "$FORWARDER_PID"
