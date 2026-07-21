#!/bin/sh
set -eu

: "${BOOTMUX_DEMO_HOME:=/tmp/bootmux-demo-home}"
: "${BOOTMUX_DEMO_NAMESPACE:=bootmux-demo}"

export HOME="$BOOTMUX_DEMO_HOME"
export CODEX_HOME="$HOME/.codex"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export HTTP_PROXY="http://10.203.0.1:3128"
export HTTPS_PROXY="$HTTP_PROXY"
export ALL_PROXY=
export NO_PROXY="localhost,127.0.0.1"

mkdir -p "$BOOTMUX_DEMO_HOME"
chmod 700 "$BOOTMUX_DEMO_HOME"
if [ -e "$CODEX_HOME/auth.json" ] || [ -x "$HOME/.local/bin/codex" ]; then
    echo "BOOTMUX_DEMO_HOME_NOT_FRESH" >&2
    exit 1
fi
if ! command -v ip >/dev/null 2>&1 || ! ip netns list | awk '{print $1}' | grep -Fx "$BOOTMUX_DEMO_NAMESPACE" >/dev/null 2>&1; then
    echo "BOOTMUX_DEMO_NAMESPACE_REQUIRED" >&2
    exit 1
fi
exec sudo ip netns exec "$BOOTMUX_DEMO_NAMESPACE" env \
    HOME="$HOME" CODEX_HOME="$CODEX_HOME" PATH="$PATH" \
    HTTP_PROXY="$HTTP_PROXY" HTTPS_PROXY="$HTTPS_PROXY" ALL_PROXY="$ALL_PROXY" NO_PROXY="$NO_PROXY" "$@"
