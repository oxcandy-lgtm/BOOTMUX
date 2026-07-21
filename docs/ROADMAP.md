# BOOTMUX Roadmap

This is the current roadmap after the Build Week integration merge and final submission. Historical gate plans and intermediate task states remain available in Git history; current public claims are controlled by the [Claim and Evidence Matrix](submission/CLAIM_EVIDENCE_MATRIX.md).

The complete original long-range plan is preserved in [Roadmap Blueprint](ROADMAP_BLUEPRINT.md). That blueprint includes speculative product and research stages and must not be read as current implementation status.

## Current state

```yaml
status_as_of: 2026-07-22_JST
build_week_submission: GREEN_SUBMITTED_OWNER_CONFIRMED
V0_companion_and_iphone_client:
  status: IMPLEMENTED
V1_physical_keyboard_path:
  status: BOUNDED_OWNER_OBSERVED_ASCII_PATH
  remaining: full controls, reconnect, repeatability
V2_terminal_return:
  status: PHYSICAL_BOOTMUX_READY_RETURN_OBSERVED
  remaining: physical selectable-copy and visible CLEAR acceptance
V3_codex_installation:
  status: GREEN_CLEAN_ARM64_VM_OFFICIAL_INSTALL_AND_HUMAN_AUTH
V4_codex_connectivity:
  status: GREEN_DIRECT_VM_COMPANION_AND_PHYSICAL_RETURN
  remaining: repeatability and physical copy acceptance
V5_optional_hotspot_and_proxy_route:
  status: RESEARCH_ROUTE_NOT_REQUIRED_FOR_BUILD_WEEK_CLAIM
V6_integrated_demo:
  status: YELLOW_GREEN_BOUNDED_PATH_REPEATABILITY_PENDING
production_ready: false
```

## Immediate priority

The Build Week submission is complete. The current priority is a judging hold rather than new feature work:

1. keep the repository, `main` links, Judge Mode, and public video available;
2. preserve the submitted evidence and claim boundaries;
3. keep the private `/feedback` Session ID and other private submission data out of the repository;
4. defer optional engineering until after submission closeout and rest.

Public demo video: https://www.youtube.com/watch?v=BNWTRxrVM6M

## Post-submission engineering

The next optional engineering milestone is a reproducible physical acceptance run:

```text
iPhone committed ASCII
→ BLE
→ ESP32-S3
→ native USB HID
→ focused target

observed target PTY / Codex
→ BOOTMUX Companion
→ local WebSocket
→ iPhone
```

Acceptance requires:

- repeated clean starts without stale-session replay;
- ENTER, BACKSPACE, CTRL-C, STOP, and RESUME behavior;
- reconnect and duplicate-suppression evidence;
- physical selectable-copy and exact paste;
- visible CLEAR feedback;
- physical HID Mirror confirmation;
- an explicit public-safe repeatability receipt.

This milestone is deferred and is not required for the already submitted Build Week entry.

## Later product milestones

### V1.1 — Physical return consolidation

Research a target Companion → USB data → ESP32-S3 → BLE → iPhone return path without weakening the current distinction between sent input and independently observed output.

### V2 — Provisioning and packaging

- simpler signed-device and firmware provisioning;
- reproducible Companion packages for additional declared platforms;
- clearer hardware compatibility profiles;
- contract-sync checks for UUIDs, protocol frames, bounds, and ports.

### V3 — Recovery workflow

Introduce policy-gated recovery only after the structured executor, approval boundary, evidence verifier, and threat model are actually implemented and tested. The current Build Week prototype does not claim this autonomous recovery layer.

### V4 — Broader input and terminal capability

Potential future work includes Unicode insertion after Companion startup, mouse input, richer terminal behavior, and continued post-bootstrap operation. None of these are part of the current public claim.

## Research boundary

The SAI-originated research program is preserved in [SAI Research Hypotheses](SAI_RESEARCH_HYPOTHESES.md), [SAI Research Roadmap](SAI_RESEARCH_ROADMAP.md), and the full [SAI Research Blueprint](SAI_RESEARCH_BLUEPRINT.md). Those documents describe concepts and evidence gates, not completed product features.

## Roadmap rules

- evidence, not code presence, closes a physical gate;
- sent input is never treated as observed target output;
- Judge Replay cannot promote a physical claim;
- unresolved capabilities remain explicit;
- production readiness is not claimed;
- security architecture is not described as enforced until its code and tests exist.
