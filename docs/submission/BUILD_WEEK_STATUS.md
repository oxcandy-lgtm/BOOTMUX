# Build Week Status

This is the public-safe operational status for the OpenAI Build Week submission path. `GREEN` means repository evidence exists; human-only gates are not marked green without confirmation.

```yaml
status_as_of: 2026-07-20 JST
submission_sprint:
  P0_toolchain: XCODE_NOT_INSTALLED_ON_APPLE_SILICON_HOST
  P1_judge_mode: GREEN
  P2_iphone_proof: PENDING
  P3_hardware_bridge: OPEN
  P4_codex_ready: OPEN
  P5_submission_package: IN_PROGRESS
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
    V1: OPEN
    V2: PARTIALLY_PROVEN_BY_V0B
    V3: OPEN
    V4: OPEN
    evidence: V0A is GREEN; V0B implementation exists but physical proof is pending
    remaining_gate: physical_iPhone_acceptance_and_copy_paste_proof
  BW4:
    status: GREEN
    evidence: standalone offline replay and live Companion /judge mode
    remaining_gate: none_for_no_rebuild_terminal_demo
  BW5:
    status: GREEN
    evidence: LICENSE and submission README headings are present
    remaining_gate: human_final_readme_review
  BW6:
    status: BLOCKED
    evidence: /feedback has not been run
    remaining_gate: feedback_not_captured
  BW7:
    status: OPEN
    evidence: no public narrated video has been created
    remaining_gate: public_video_with_voice_narration
  BW8:
    status: IN_PROGRESS
    evidence: final Devpost draft, demo script, and checklist are present
    remaining_gate: final_human_review_and_video_upload
  BW9:
    status: OPEN
    evidence: final submission has not been made
    remaining_gate: human_submission_confirmation
```

## Current technical boundary

V0A Companion Core is locally verified. The claim boundary remains: no real iPhone-to-BLE-to-ESP32-S3 input, native USB HID enumeration, mouse support, Codex installation, offline target operation, or continued post-boot operation is proven by this repository state.

## Explicit human and tool-use state

```yaml
registration: HUMAN_CONFIRMATION_PENDING
license:
  status: GREEN_MIT_APPROVED
  file_added: true
feedback:
  command_run: false
  reason: V0B_to_V4_not_complete
github_issues_accessed: false
github_actions_used: false
```
