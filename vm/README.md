# BOOTMUX ARM64 VM demo harness

This directory describes a bounded, disposable ARM64 Linux demo environment.
It does not install a VM provider, persist credentials, or change the host.
Lima is the canonical provider when it is already installed.

The clean instance is `bootmux-clean`; a demo instance may be created as
`bootmux-demo` only after the clean baseline is verified. A missing provider is
an environmental blocker, not a successful VM proof.

The VM runs Companion on loopback port 8765. A bounded host TCP forwarder can
expose that port on a deliberately selected local interface for the iPhone.
The forwarder does not parse WebSocket data or log payloads. Its public-safe
diagnostic log contains only `FORWARDER_READY`, monotonic connection IDs, and
the lifecycle markers `CONNECTION_ACCEPTED`, `TARGET_CONNECTED`, and
`CONNECTION_CLOSED`.

The canonical HID transcript path is the VM-relative
`.bootmux/hid-transcript`. `vm/run-physical-demo.sh` passes that relative value
to the VM shell, where `$HOME` is expanded. Companion and
`/tmp/bootmux-source/vm/start-hid-target.sh` therefore use the same path; the
host's `$HOME` is never embedded in the VM command. The launcher prints the
exact focused-target command using the provisioned VM copy.

`start-hid-target.sh` keeps the transcript private (`0600`) and treats the
configured byte threshold as a fail-closed limit. It terminates the PTY
writer with `HID_TARGET_TRANSCRIPT_LIMIT_EXCEEDED` rather than unlinking or
replacing a file while the writer owns an open descriptor; cleanup removes the
transcript after termination. This is an explicit termination policy, not
silent output truncation.

Launcher diagnostics distinguish an unavailable Lima command
(`reason=LIMA_COMMAND_UNAVAILABLE`) from a missing configured instance
(`reason=INSTANCE_NOT_FOUND`). `LIMA_BIN` may be used for a local provider
override. A successful launcher printout is not physical HID evidence until
the owner confirms the focused target and iPhone path.

For a bounded owner-run setup, `vm/run-physical-demo.sh` checks the existing
`bootmux-demo` Lima instance and Companion, starts only its own Companion and
forwarder children, prints the local iPhone WebSocket endpoint at runtime, and
cleans those children on exit. It does not start or claim a focused Terminal
window; run `vm/start-hid-target.sh` in that focused window. The optional
Companion `/v1/mirror` endpoint is read-only and observes that private bounded
transcript without synthesizing output from iPhone input.

No credentials, auth URLs, IP addresses, SSIDs, hostnames, usernames, or VM
private paths belong in committed evidence.
