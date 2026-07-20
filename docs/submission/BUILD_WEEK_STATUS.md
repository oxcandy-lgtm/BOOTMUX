# Build Week Status

This is the public-safe operational status for the OpenAI Build Week submission path. `GREEN` means repository evidence exists; human-only gates are not marked green without confirmation.

```yaml
status_as_of: 2026-07-21 JST
submission_sprint:
  P0_toolchain: IN_PROGRESS
  P1_judge_mode: GREEN
  P2_iphone_proof: PENDING
  P3_hardware_bridge: IN_PROGRESS
  P4_codex_ready: GREEN_BOUNDED_LOCAL_RUN
  P5_submission_package: READY
feature_development: REOPENED_ONLY_FOR_V1_PHYSICAL_GATE
gates:
  BW0:
    status: IN_PROGRESS
    evidence: docs/submission/BUILD_WEEK_STATUS.md
    remaining_gate: REGISTRATION_CONFIRMATION_PENDING
  BW1:
    status: IN_PROGRESS
    primary_codex_thread: CONFIRMED
    majority_core_work: IN_PROGRESS
    gpt_5_6_evidence: IN_PROGRESS
    evidence: docs/submission/CODEX_GPT56_EVIDENCE_LEDGER.md
    remaining_gate: CONTINUE_PRIMARY_THREAD_THROUGH_V4_AND_RUN_FEEDBACK_LATER
  BW2:
    status: IMPLEMENTED
    evidence: docs/submission/BUILD_WEEK_SCOPE_LEDGER.md
    remaining_gate: PRIVATE_CONCEPT_DATE_OPTIONAL_OWNER_CONFIRMATION
  BW3:
    status: IN_PROGRESS
    V0A: GREEN
    V0B: IMPLEMENTED_AWAITING_PHYSICAL_IPHONE_PROOF
    V1: R7_BLE_TRANSPORT_STABILITY_VERIFIED_FULL_ACCEPTANCE_PENDING
    V2: VM_CODEX_PROBE_GREEN_PHYSICAL_RETURN_PENDING
    V3: VM_CODEX_ADAPTER_GREEN_PHYSICAL_RETURN_PENDING
    V4: GREEN_BOUNDED_LOCAL_AND_VM_PROBE
    evidence: docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md; launch canvas and short BLE/HID transport path are physically observed; full control-key and stability acceptance is not yet recorded
    remaining_gate: backspace_ctrl_c_stop_resume_duplicate_reconnect_and_full_stability_receipt
  BW4:
    status: GREEN
    evidence: standalone offline replay and live Companion /judge mode
    remaining_gate: none_for_no_rebuild_terminal_demo
  BW5:
    status: GREEN
    evidence: LICENSE and submission README headings are present
    remaining_gate: human_final_readme_review
  BW6:
    status: READY
    evidence: Primary Codex Thread confirmed; /feedback has not been run
    remaining_gate: OWNER_ACTION_RUN_FEEDBACK_AND_KEEP_SESSION_ID_PRIVATE
  BW7:
    status: READY_SCRIPT_ONLY
    evidence: docs/submission/DEMO_SCRIPT.md
    remaining_gate: public_video_with_voice_narration
  BW8:
    status: READY_FOR_HUMAN_REVIEW
    evidence: final Devpost draft, demo script, and checklist are present
    remaining_gate: final_human_review_and_video_upload
  BW9:
    status: OPEN
    evidence: final submission has not been made
    remaining_gate: human_submission_confirmation
```

## V2–V6 integrated Codex return progress

The real ARM64 Lima VM, official Codex CLI authentication, direct
BOOTMUX_READY probe, and production Companion codex_prompt probe are GREEN
locally. Physical iPhone return and copy remain unproven because the
device-side terminal session has not yet reached TERM ON through the
currently active LAN endpoint. See
[V2–V6 Codex Physical Return Progress](../evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md).

The iOS client now includes the required local IP/CIDR ATS exceptions for
iOS 17+, and its Settings actions are visually separated into CONNECT,
DISCONNECT, CLEAR, and SEND rows. This does not upgrade the physical claim
until a fresh signed install observes BOOTMUX_READY on the iPhone.

## Current technical boundary

V0A Companion Core is locally verified. The short iPhone-to-BLE transport path and native USB HID ASCII path are observed; the complete V1 keyboard acceptance, mouse support, Codex installation, offline target operation, and continued post-boot operation are not proven by this repository state.

## Explicit human and tool-use state

```yaml
registration: HUMAN_CONFIRMATION_PENDING
license:
  status: GREEN_MIT_APPROVED
  file_added: true
feedback:
  captured_privately: true
  public_session_id: false
github_issues_accessed: false
github_actions_used: false
```
