#!/bin/sh
set -eu
command -v limactl >/dev/null 2>&1 || { echo "VM_PROVIDER_UNAVAILABLE" >&2; exit 78; }
INSTANCE=${1:-bootmux-demo}
limactl shell "$INSTANCE" -- sh -lc '
  set -eu
  getent hosts api.openai.com >/dev/null
  if curl --fail --silent --show-error --max-time 15 -o /dev/null https://api.openai.com/; then :; else test "$?" -eq 22; fi
  echo DNS_PASS
  echo TLS_HTTP_REACHABILITY_PASS
  echo VM_NAT_EGRESS_PASS
'
