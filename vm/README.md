# BOOTMUX ARM64 VM demo harness

This directory describes a bounded, disposable ARM64 Linux demo environment.
It does not install a VM provider, persist credentials, or change the host.
Lima is the canonical provider when it is already installed.

The clean instance is `bootmux-clean`; a demo instance may be created as
`bootmux-demo` only after the clean baseline is verified. A missing provider is
an environmental blocker, not a successful VM proof.

The VM runs Companion on loopback port 8765. A bounded host TCP forwarder can
expose that port on a deliberately selected local interface for the iPhone.
The forwarder does not parse WebSocket data or log payloads.

No credentials, auth URLs, IP addresses, SSIDs, hostnames, usernames, or VM
private paths belong in committed evidence.
