# Integrated demo runbook

1. Run `run-integrated-demo.sh` and retain the clean-state result.
2. Start Companion with `start-companion.sh`.
3. Start `start-host-forwarder.sh` only while the demo is active.
4. Open the focused VM shell and prove the Codex-absent state.
5. From the physical iPhone HID path, run `bash ~/bootmux/install-codex.sh` and press ENTER.
6. Complete official Codex authentication manually when prompted.
7. Use the iPhone terminal endpoint to run the bounded `BOOTMUX_READY` prompt.
8. Select and copy the returned output, then stop all demo processes.

Provider, network, official installation, and authentication failures remain
explicit environmental or human gates; they are never marked GREEN silently.
