# Build Week Status

This is the public-safe operational status for the OpenAI Build Week submission path. `GREEN` means repository evidence exists; human-only gates are not marked green without confirmation.

```yaml
status_as_of: 2026-07-21 JST
submission_sprint:
  P0_toolchain: IN_PROGRESS
  P1_judge_mode: GREEN
  P2_iphone_proof: PHYSICAL_BOOTMUX_READY_OBSERVED_COPY_PENDING
  P3_hardware_bridge: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
  P4_codex_ready: GREEN_BOUNDED_LOCAL_RUN
  P5_submission_package: READY_FINAL_VIDEO_PENDING
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
    feedback_receipt: CAPTURED_PRIVATELY
    evidence: docs/submission/CODEX_GPT56_EVIDENCE_LEDGER.md
    remaining_gate: COMPLETE_FINAL_PUBLIC_SAFE_EVIDENCE_MAPPING
  BW2:
    status: IMPLEMENTED
    evidence: docs/submission/BUILD_WEEK_SCOPE_LEDGER.md
    remaining_gate: PRIVATE_CONCEPT_DATE_OPTIONAL_OWNER_CONFIRMATION
  BW3:
    status: IN_PROGRESS
    V0A: GREEN
    V0B: IMPLEMENTED_PHYSICAL_BOOTMUX_READY_OBSERVED
    V1: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
    V2: VM_CODEX_PROBE_GREEN_PHYSICAL_RETURN_PENDING_COPY_REPEATABILITY
    V3: VM_CODEX_ADAPTER_GREEN_PHYSICAL_RETURN_PENDING_COPY_REPEATABILITY
    V4: GREEN_BOUNDED_LOCAL_AND_VM_PROBE
    evidence: docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md; launch canvas and short BLE/HID transport path are physically observed; full control-key and stability acceptance is not yet recorded
    remaining_gate: selectable_copy_clear_feedback_and_repeatability_receipt
  BW4:
    status: GREEN
    evidence: standalone offline replay and live Companion /judge mode
    remaining_gate: none_for_no_rebuild_terminal_demo
  BW5:
    status: GREEN
    evidence: LICENSE and submission README headings are present
    remaining_gate: human_final_readme_review
  BW6:
    status: GREEN_PRIVATE_CAPTURED
    evidence: owner-confirmed private /feedback receipt; Session ID intentionally excluded from the public repository
    remaining_gate: preserve_private_session_id_for_submission
  BW7:
    status: IN_PROGRESS_TWO_EDITED_SEGMENTS_COMPLETE
    evidence: docs/submission/DEMO_SCRIPT.md; narrated 17.233-second opening; narrated 36.700-second HID SEND function test
    completed_duration_seconds: 53.933
    recommended_final_duration_seconds: 125
    remaining_recommended_seconds: 71.067
    remaining_gate: integrated_codex_return_copy_clear_architecture_judge_closeout_final_edit_privacy_review_and_public_upload
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
`BOOTMUX_READY` probe, and production Companion `codex_prompt` probe are GREEN
locally. The owner has also observed the physical iPhone return through the
Companion. Selectable copy, visible CLEAR feedback, and repeatability remain
pending. See
[V2–V6 Codex Physical Return Progress](../evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md).

The iOS client now includes the required local IP/CIDR ATS exceptions for
iOS 17+, and its Settings actions are visually separated into CONNECT,
DISCONNECT, CLEAR, and SEND rows. This does not upgrade the physical claim.
The physical claim is limited to the owner-observed bounded ASCII path and
`BOOTMUX_READY` return; it does not claim repeatability or production readiness.

R3 lifecycle repair is code-green locally: inactive no longer disconnects,
failed sessions can reconnect directly, and CLEAR visibly resets output,
sanitizer, pending publication, and failed state. The latest signed app was
installed and launched. The subsequent fresh endpoint run reached Safari
Judge, TERM ON, and physical `BOOTMUX_READY` through the VM Companion. Copy,
CLEAR, and repeatability remain owner-confirmation gates.

## Video production status

Two narrated 16:9 segments are complete locally:

1. **17.233 seconds — opening:** dirty-display problem setup, ESP32-S3 reveal, English narration and subtitles, screen treatment, and `BOOT GPT-5.6` / BOOTMUX title.
2. **36.700 seconds — HID SEND function test:** BLE connection, ENTER twice, `hello`, HID SEND, observed physical terminal reflection, separate operation callouts, public-safe redaction, and a BLE batch → ESP32-S3 → USB HID technical card.

Completed duration is **53.933 seconds**. The hard three-minute allowance leaves **126.067 seconds**, but the recommended final master is approximately **125 seconds**, leaving only **71.067 seconds** of useful remaining footage. The next required proof is the integrated Codex `BOOTMUX_READY` return to the iPhone, followed by copy/CLEAR acceptance when available, the asymmetric transport explanation, Judge Mode, Codex/GPT-5.6 attribution, honest limitations, final privacy review, and public upload.

## Current technical boundary

V0A Companion Core is locally verified. The short iPhone-to-BLE transport path and native USB HID ASCII path are observed, and official Codex installation plus bounded `BOOTMUX_READY` probes are GREEN in the clean ARM64 Lima VM. The complete repeatable V1 keyboard acceptance, selectable physical copy, visible CLEAR acceptance, mouse support, offline target operation, and continued post-boot operation are not proven by this repository state.

## Explicit human and tool-use state

```yaml
registration: HUMAN_CONFIRMATION_PENDING
license:
  status: GREEN_MIT_APPROVED
  file_added: true
feedback:
  captured_privately: true
  public_session_id: false
video:
  opening_segment_complete: true
  opening_duration_seconds: 17.233
  hid_send_segment_complete: true
  hid_send_duration_seconds: 36.700
  completed_duration_seconds: 53.933
  recommended_final_duration_seconds: 125
  remaining_recommended_seconds: 71.067
  final_public_video_complete: false
  public_upload_complete: false
github_issues_accessed: false
github_actions_used: false
```