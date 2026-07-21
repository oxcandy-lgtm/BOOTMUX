# V4 Codex App Interaction — Historical Checkpoint

This file preserves the bounded adapter checkpoint before live authentication and physical return. It is not the current project state.

The later closeout in [`V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md`](V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md) records successful official Codex execution through both the direct VM path and the production Companion adapter, followed by a physical `BOOTMUX_READY` return to the iPhone.

## Original checkpoint

```yaml
status: ADAPTER_TESTED_AUTH_AND_PHYSICAL_RETURN_PENDING
codex_protocol: codex_prompt_codex_cancel_codex_new_session
prompt_limit_bytes: 8192
output_limit_bytes: 131072
timeout_seconds: 180
adapter_fake_process_tests: PASS
BOOTMUX_READY: NOT_RUN_AUTH_REQUIRED
physical_iPhone_response: NOT_PROVEN
copy: NOT_RUN
claim: not_green
private_identifiers_recorded: false
```

## Current reconciliation

```yaml
codex_protocol: codex_prompt_codex_cancel_codex_new_session
prompt_limit_bytes: 8192
output_limit_bytes: 131072
timeout_seconds: 180
adapter_tests: PASS
official_codex_executable_in_vm: PASS
human_authentication: PASS
direct_vm_BOOTMUX_READY: PASS
companion_codex_prompt_BOOTMUX_READY: PASS
physical_iPhone_response: PASS_OWNER_OBSERVED
physical_selectable_copy: PENDING
clear_feedback: PENDING
repeatability: PENDING
production_ready: false
private_identifiers_recorded: false
```

The adapter remains a bounded one-shot prototype. It is not presented as a production agent service or proof of continued post-bootstrap operation.