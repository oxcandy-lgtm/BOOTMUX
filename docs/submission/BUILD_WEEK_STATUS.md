# Build Week Status

This is the public-safe operational status for the OpenAI Build Week submission path. `GREEN` means repository evidence exists. Human-only and organizer-facing actions are not marked complete without explicit confirmation.

```yaml
status_as_of: 2026-07-22_JST
category: DEVELOPER_TOOLS
submission_sprint:
  toolchain_and_companion: GREEN_WITH_DECLARED_LIMITS
  no_build_judge_mode: GREEN
  iphone_client: IMPLEMENTED_PHYSICAL_BOOTMUX_READY_OBSERVED
  physical_bridge: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
  codex_ready: CLEAN_VM_AND_PHYSICAL_RETURN_OBSERVED
  submission_package: READY_PUBLIC_UPLOAD_AND_FINAL_SUBMIT_PENDING
feature_development: FROZEN_OUTSIDE_SUBMISSION_BLOCKERS
```

## Gate status

| Gate | Status | Evidence or remaining action |
| --- | --- | --- |
| BW0 — registration and category | GREEN_OWNER_CONFIRMED | Individual entry, Japan, Developer Tools selected in Devpost |
| BW1 — Codex and GPT-5.6 evidence | GREEN | Public evidence ledger plus private Primary Build Thread receipt |
| BW2 — scope ledger | GREEN_PUBLIC_LEDGER | Final human claims remain bounded by the claim matrix |
| BW3 — working implementation | BOUNDED_DEMO_GREEN | Physical bounded ASCII and `BOOTMUX_READY` observed; repeatability and usability gates remain explicit |
| BW4 — no-build judge path | GREEN | Standalone replay plus packaged/live Companion Judge Mode |
| BW5 — repository package | GREEN | MIT license, README, setup, supported platforms, and testing path |
| BW6 — `/feedback` | GREEN_PRIVATE_CAPTURED_AND_ENTERED | Real Session ID intentionally excluded from the public repository |
| BW7 — narrated demo | FINAL_MASTER_COMPLETE_OWNER_REPORTED | Public YouTube upload, visibility, duration, audio, and signed-out link check remain |
| BW8 — Devpost fields | READY_FINAL_LINK_REVIEW | Project copy, category, repository, judge instructions, and developer-tool testing path populated |
| BW9 — final submission | OPEN | Terms acceptance and successful `Submit project` confirmation remain human actions |

## Competition positioning

> **The physical first mile for Codex. Built by Codex. Architected and hardened with GPT-5.6.**

```text
Codex
  implemented and repaired the Go Companion, native SwiftUI client,
  ESP32-S3 firmware, ARM64 VM harness, bounded Codex adapter,
  Judge Mode, tests, probes, and validation tooling

GPT-5.6
  designed the asymmetric physical-input / observed-output architecture,
  bounded contracts, adversarial reviews, root-cause repairs,
  claim boundaries, and submission convergence

Human
  selected the problem and product direction, performed hardware setup,
  made real-device observations, accepted or rejected repairs,
  edited the final video, and owns every public claim and submission action
```

The central result is recursive but concrete: Codex helped build BOOTMUX, and BOOTMUX then carried a real target-side Codex interaction through the demonstrated system and returned `BOOTMUX_READY` to the physical iPhone.

## Current technical boundary

Demonstrated or owner-observed:

- Go Companion PTY/WebSocket core;
- native SwiftUI iPhone implementation;
- bounded BLE transport and native USB HID ASCII delivery;
- official Codex CLI installation and bounded probes in a clean ARM64 Lima VM;
- physical `BOOTMUX_READY` return to the iPhone;
- standalone, packaged, and live local Judge Mode.

Not claimed as complete:

- repeatable production-ready physical operation;
- physical selectable-copy acceptance;
- visible CLEAR acceptance;
- physical HID Mirror acceptance;
- Unicode HID or mouse support;
- complete offline target operation;
- full terminal emulation;
- continued post-bootstrap operation.

## Submission closeout

```yaml
registration_and_category:
  status: GREEN_OWNER_CONFIRMED
  submitter_type: INDIVIDUAL
  country: JAPAN
  category: DEVELOPER_TOOLS
feedback:
  captured_privately: true
  entered_in_devpost: true
  public_session_id: false
video:
  final_master_complete: true
  completion_source: OWNER_CONFIRMATION
  public_youtube_upload: PENDING_CONFIRMATION
  public_visibility_check: PENDING
  under_three_minutes_check: PENDING_FINAL_VERIFICATION
  narration_covers_product_codex_and_gpt_5_6: PENDING_FINAL_PLAYBACK_VERIFICATION
devpost:
  form_fields_prepared: true
  terms_accepted: PENDING
  final_submit_confirmed: false
github_actions_used: false
github_issues_used: false
```

The remaining submission-critical sequence is:

1. upload the final master to YouTube as **Public**;
2. verify duration, narration, audio, and visibility in a signed-out browser;
3. add the final video URL to Devpost and optionally to this repository;
4. recheck all public links;
5. accept the rules and terms;
6. submit and confirm that the Devpost entry is no longer a draft.
