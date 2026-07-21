# R7D Safe VM Recovery

This document records the bounded implementation path for the disposable demo
environment. It does not claim physical S3 proxy or Codex authentication proof.

## Safety boundary

- The Mac Wi-Fi interface remains the normal default route.
- No Mac route, DNS, service-order, VPN, or Wi-Fi setting is changed by the
  demo scripts.
- USB Ethernet is not used as a gateway and is outside the recovery core.
- The demo shell refuses to run without the named Linux network namespace and
  refuses a home that already contains `auth.json` or a local `codex` binary.

## Recovery path

```text
demo namespace (no default route)
  -> 10.203.0.1 VM relay
  -> host.lima.internal:33128 Mac forwarder
  -> S3 Wi-Fi STA:3128 CONNECT proxy
  -> HTTPS destination:443
```

The Mac forwarder keeps loopback as its default listener. When a Lima VM is
used, the runtime invocation binds only to the Lima host-facing surface and
allowlists the disposable VM subnet; it does not bind the Mac Wi-Fi address.
The relay and forwarder continue accepting bounded new attempts after a
transient target refusal.

The S3 proxy accepts only bounded `CONNECT host:443 HTTP/1.1` requests. It uses
one client, a 4096-byte request-header limit, 4096-byte relay buffers, a
15-second connection bound, and a 300-second idle bound. It binds to the
current Wi-Fi STA address only after `WIFI_ONLINE`; it is stopped on Wi-Fi
disconnect. Hostnames, URLs, credentials, device codes, and tokens are not
logged.

BLE status is reported as `BMX1|PROXY_STATUS|session|sequence|STATUS`.
The current runtime emits `PROXY_OFFLINE`, `PROXY_READY`, and
`PROXY_ERROR`; `PROXY_ACTIVE` is reserved in the protocol for a future
per-tunnel notification and is not claimed as emitted by this implementation.

## Local proof currently available

The following was executed in the ARM64 Lima `bootmux-clean` VM:

```text
namespace created: bootmux-demo
route: 10.203.0.0/30 dev bmux-demo
default route: absent
direct HTTPS: blocked before proxy configuration
```

The actual S3 Wi-Fi listener, CONNECT tunnel, Codex installation, device
authentication, and `BOOTMUX_RECOVERED` conversation remain physical/runtime
gates until the S3 is flashed with the new image, reaches `WIFI_ONLINE`, and a
private endpoint is supplied at runtime. No private endpoint or credential is
stored here.
