#!/bin/sh
set -eu

NAMESPACE=${BOOTMUX_DEMO_NAMESPACE:-bootmux-demo}
HOST_LINK=${BOOTMUX_DEMO_HOST_LINK:-bmux-host}
DEMO_LINK=${BOOTMUX_DEMO_LINK:-bmux-demo}
HOST_ADDR=${BOOTMUX_DEMO_HOST_ADDR:-10.203.0.1/30}
DEMO_ADDR=${BOOTMUX_DEMO_ADDR:-10.203.0.2/30}

if [ "${1:-}" = "--down" ]; then
    if ip netns list | awk '{print $1}' | grep -Fx "$NAMESPACE" >/dev/null 2>&1; then
        ip netns delete "$NAMESPACE"
    fi
    if ip link show "$HOST_LINK" >/dev/null 2>&1; then
        ip link delete "$HOST_LINK"
    fi
    exit 0
fi

if [ "$#" -ne 0 ]; then
    echo "usage: $0 [--down]" >&2
    exit 2
fi

if ip netns list | awk '{print $1}' | grep -Fx "$NAMESPACE" >/dev/null 2>&1 ||
   ip link show "$HOST_LINK" >/dev/null 2>&1 ||
   ip link show "$DEMO_LINK" >/dev/null 2>&1; then
    echo "demo namespace or veth already exists; use --down only for this exact demo nameset" >&2
    exit 1
fi

ip netns add "$NAMESPACE"
ip link add "$HOST_LINK" type veth peer name "$DEMO_LINK"
ip link set "$DEMO_LINK" netns "$NAMESPACE"
ip addr add "$HOST_ADDR" dev "$HOST_LINK"
ip link set "$HOST_LINK" up
ip -n "$NAMESPACE" addr add "$DEMO_ADDR" dev "$DEMO_LINK"
ip -n "$NAMESPACE" link set lo up
ip -n "$NAMESPACE" link set "$DEMO_LINK" up

echo "BOOTMUX_DEMO_NAMESPACE_READY"
echo "default route intentionally absent"
