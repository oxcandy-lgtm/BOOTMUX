# V3 Codex Clean VM Install — Historical Checkpoint

This file preserves the checkpoint reached before human authentication. It is not the current project state.

The later closeout in [`V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md`](V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md) records successful human-controlled authentication, direct Codex execution, the production Companion `codex_prompt` path, and a physical `BOOTMUX_READY` return to the iPhone.

## Original checkpoint

```yaml
status: OFFICIAL_INSTALL_PASS_AUTH_PENDING
clean_arm64_vm: PASS
codex_absent_initially: PASS
official_installer: vm/install-codex.sh
installation_trigger_from_iPhone_HID: NOT_PROVEN
node_runtime: OFFICIAL_NODE_ARM64_USER_LOCAL
version_proof: codex-cli_0.144.6
authentication: HUMAN_CONTROLLED_NOT_RUN
claim: not_green
blocker: HUMAN_CODEX_AUTHENTICATION
private_identifiers_recorded: false
```

## Current reconciliation

```yaml
clean_arm64_vm: PASS
codex_absent_initially: PASS
official_install: PASS
codex_version: codex-cli_0.144.6
human_controlled_authentication: PASS
direct_codex_prompt: PASS
direct_marker: BOOTMUX_READY
companion_codex_prompt: PASS
physical_iphone_return: PASS_OWNER_OBSERVED
installation_trigger_from_iPhone_HID: OWNER_OBSERVED_BOUNDED_PATH
continued_post_boot_operation: NOT_PROVEN
production_ready: false
private_identifiers_recorded: false
```

Authentication secrets and private URLs remain excluded. This receipt supports only the declared clean-VM and bounded demonstrated path.