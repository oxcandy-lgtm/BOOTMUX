# Build Week Status

This is the public-safe operational status for the OpenAI Build Week submission path. `GREEN` means repository evidence exists; human-only gates are not marked green without confirmation.

```yaml
status_as_of: 2026-07-21_JST
submission_sprint:
  P0_toolchain: GREEN_WITH_DECLARED_LOCAL_LIMITS
  P1_judge_mode: GREEN
  P2_iphone_proof: PHYSICAL_BOOTMUX_READY_OBSERVED_COPY_PENDING
  P3_hardware_bridge: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
  P4_codex_ready: DIRECT_VM_COMPANION_AND_PHYSICAL_RETURN
  P5_submission_package: READY_FINAL_VIDEO_AND_SUBMISSION_PENDING
feature_development: FROZEN_OUTSIDE_SUBMISSION_BLOCKERS

gates:
  BW0:
    status: IN_PROGRESS
    evidence: docs/submission/BUILD_WEEK_STATUS.md
    remaining_gate: REGISTRATION_AND_TRACK_CONFIRMATION

  BW1:
    status: GREEN_PUBLIC_EVIDENCE_PRIVATE_RECEIPT
    primary_codex_thread: CONFIRMED
    majority_core_work: COMPLETE
    gpt_5_6_evidence: GREEN_PUBLIC_EVIDENCE_MAPPING
    feedback_receipt: CAPTURED_PRIVATELY
    evidence: docs/submission/CODEX_GPT56_EVIDENCE_LEDGER.md
    remaining_gate: PRESERVE_PRIVATE_SESSION_ID_AND_EXPLAIN_BOTH_TOOLS_IN_FINAL_VIDEO

  BW2:
    status: IMPLEMENTED
    evidence: docs/submission/BUILD_WEEK_SCOPE_LEDGER.md
    remaining_gate: FINAL_HUMAN_SCOPE_REVIEW

  BW3:
    status: IN_PROGRESS_PHYSICAL_USABILITY_AND_REPEATABILITY_PENDING
    V0A: GREEN
    V0B: IMPLEMENTED_PHYSICAL_BOOTMUX_READY_OBSERVED
    V1: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
    V2: PHYSICAL_RETURN_OBSERVED_COPY_REPEATABILITY_PENDING
    V3: CLEAN_VM_CODEX_INSTALL_AND_ADAPTER_GREEN
    V4: PHYSICAL_CODEX_RETURN_OBSERVED
    HID_MIRROR: CODE_GREEN_PHYSICAL_CONFIRMATION_PENDING
    evidence: docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md; docs/evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md
    remaining_gate: SELECTABLE_COPY_CLEAR_HID_MIRROR_AND_REPEATABILITY

  BW4:
    status: GREEN
    evidence: standalone offline replay and live Companion /judge mode
    remaining_gate: none_for_no_rebuild_terminal_demo

  BW5:
    status: GREEN
    evidence: LICENSE, README, installation, supported-platform, and judge-test instructions
    remaining_gate: FINAL_HUMAN_README_AND_LINK_REVIEW

  BW6:
    status: GREEN_PRIVATE_CAPTURED
    evidence: owner-confirmed private /feedback receipt; Session ID intentionally excluded from the public repository
    remaining_gate: ENTER_PRIVATE_SESSION_ID_IN_DEVPOST

  BW7:
    status: IN_PROGRESS_TWO_EDITED_SEGMENTS_COMPLETE
    evidence: docs/submission/DEMO_SCRIPT.md; narrated 17.233-second opening; narrated 36.700-second HID SEND function test
    completed_duration_seconds: 53.933
    recommended_final_duration_seconds: 125
    remaining_recommended_seconds: 71.067
    remaining_gate: integrated_codex_return_copy_clear_architecture_judge_closeout_final_edit_privacy_review_and_public_upload

  BW8:
    status: READY_FOR_HUMAN_REVIEW
    evidence: Devpost drafts, official-rule summary, Codex/GPT-5.6 ledger, demo script, and checklist
    remaining_gate: RULES_RECHECK_SIGNED_OUT_LINK_CHECK_AND_DEVPOST_DRAFT

  BW9:
    status: OPEN
    evidence: final submission has not been confirmed
    remaining_gate: HUMAN_SUBMISSION_CONFIRMATION
```

## Competition positioning

BOOTMUX is positioned as:

> **The physical first mile for Codex. Built by Codex. Architected and hardened with GPT-5.6.**

This maps directly to the Build Week requirements:

```text
Codex
  implemented the Go Companion, SwiftUI app, ESP32-S3 firmware,
  VM harness, Codex adapter, Judge Mode, tests, and repair cycles

GPT-5.6
  designed the asymmetric physical-input / observed-output architecture,
  bounded contracts, adversarial reviews, and public evidence boundaries

Human
  selected the problem and product direction, performed physical setup,
  accepted repairs, recorded evidence, and owns the final submission
```

The central result is recursive but concrete: Codex helped build BOOTMUX, and BOOTMUX then carried a real Codex prompt through the system and returned `BOOTMUX_READY` to the physical iPhone.

## What BOOTMUX is required to prove

For this competition, BOOTMUX does not need to become a complete remote-administration suite. It must present the smallest coherent Developer Tools product that demonstrates:

1. a real problem before normal AI or remote-development access is ready;
2. physical iPhone → BLE → ESP32-S3 → USB HID input;
3. independently observed target or Codex output returning through the Companion;
4. meaningful, specific Codex implementation work;
5. meaningful, specific GPT-5.6 architecture and verification work;
6. a runnable no-rebuild judge path;
7. an honest boundary between demonstrated and future features.

See [OpenAI Build Week Requirements](../OPENAI_BUILD_WEEK.md) for the official-rule mapping.

## Integrated Codex return progress

The real ARM64 Lima VM, official Codex CLI authentication, direct `BOOTMUX_READY` probe, and production Companion `codex_prompt` probe are GREEN locally. The owner also observed the physical iPhone return through the Companion.

The physical claim is limited to the owner-observed bounded ASCII path and `BOOTMUX_READY` return. It does not claim repeatability or production readiness.

Selectable copy, visible CLEAR feedback, physical HID Mirror, and repeatability remain owner-confirmation gates.

## Video production status

Two narrated 16:9 segments are complete locally:

1. **17.233 seconds — opening:** dirty-display problem setup, ESP32-S3 reveal, English narration and subtitles, screen treatment, and `BOOT GPT-5.6` / BOOTMUX title.
2. **36.700 seconds — HID SEND function test:** BLE connection, ENTER twice, `hello`, HID SEND, observed physical terminal reflection, separate operation callouts, public-safe redaction, and a BLE batch → ESP32-S3 → USB HID technical card.

Completed duration is **53.933 seconds**. The hard three-minute allowance leaves **126.067 seconds**, but the recommended final master is approximately **125 seconds**, leaving **71.067 seconds** of useful remaining footage.

The next required footage is:

1. integrated physical Codex `BOOTMUX_READY` return to the iPhone;
2. COPY/CLEAR acceptance when available;
3. the asymmetric transport explanation;
4. explicit Codex and GPT-5.6 attribution;
5. short Judge Mode proof;
6. honest limitations and closing claim.

The final video must specifically explain how Codex built the major layers and how GPT-5.6 designed and hardened the architecture. Showing the model names without concrete contributions is insufficient.

## Current technical boundary

V0A Companion Core is locally verified. The short iPhone-to-BLE transport path and native USB HID ASCII path are observed, and official Codex installation plus bounded `BOOTMUX_READY` probes are GREEN in the clean ARM64 Lima VM.

The project does not currently claim:

- repeatable full physical operation;
- selectable copy acceptance;
- visible CLEAR acceptance;
- physical HID Mirror acceptance;
- Unicode HID;
- mouse support;
- complete offline target operation;
- a full terminal emulator;
- production readiness.

## Explicit human and tool-use state

```yaml
registration: HUMAN_CONFIRMATION_PENDING
track: DEVELOPER_TOOLS_INTENDED
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
