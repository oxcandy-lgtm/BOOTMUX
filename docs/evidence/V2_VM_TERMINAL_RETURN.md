# V2 VM Terminal Return — Historical Checkpoint

This file preserves an early pre-success checkpoint. It is not the current project state.

The later append-only closeout in [`V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md`](V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md) records that the iPhone reached the Mac forwarder, the forwarder reached the VM Companion, `TERM ON` passed, and a physical `BOOTMUX_READY` return reached the iPhone. Physical selectable-copy, CLEAR feedback, and repeatability remain unresolved.

## Original checkpoint

```yaml
status: VM_RUNTIME_PASS_PHYSICAL_IPHONE_PENDING
companion_adapter: existing_versioned_websocket_terminal
vm_companion: ARM64_LIMA_RUNTIME_PASS
clean_recreate: PASS
host_port_forward: PASS
live_judge_probe: PASS
physical_iPhone_to_VM_WebSocket: NOT_RUN
stdout_return: NOT_PROVEN
selectable_output: IMPLEMENTED_BY_EXISTING_TERMINAL_VIEW
claim: not_green
blocker: PHYSICAL_IPHONE_NETWORK_AND_COPY_PROOF
private_identifiers_recorded: false
```

## Current reconciliation

```yaml
physical_iPhone_to_VM_WebSocket: PASS_OWNER_OBSERVED
stdout_and_codex_return: PASS_OWNER_OBSERVED
BOOTMUX_READY: PASS_OWNER_OBSERVED
physical_selectable_copy: PENDING
clear_feedback: PENDING
repeatability: PENDING
production_ready: false
```

The historical failure remains evidence of the earlier gate; it must not override the later success receipt or promote the still-pending usability gates.