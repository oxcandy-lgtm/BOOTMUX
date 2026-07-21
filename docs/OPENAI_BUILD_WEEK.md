# OpenAI Build Week Requirements for BOOTMUX

This is BOOTMUX's public operational summary. The Official Rules and Devpost form remain controlling whenever this file conflicts with them.

```yaml
verified_at: 2026-07-21_JST
competition: OpenAI Build Week
category: Developer Tools
source_of_truth: https://openai.devpost.com/rules
supporting_faq: https://openai.devpost.com/details/faqs
submission_deadline:
  pacific: 2026-07-21T17:00:00-07:00
  japan: 2026-07-22T09:00:00+09:00
```

## Required submission package

BOOTMUX's working interpretation of the official requirements is:

1. build a real, non-trivial project with Codex and GPT-5.6;
2. explain the project and both tools' meaningful contributions;
3. select one category;
4. provide a public YouTube demo under three minutes with clear narration;
5. provide a repository that judges can access and test;
6. include relevant licensing or the required private-repository sharing;
7. provide the Primary Build Thread `/feedback` Session ID privately in Devpost;
8. provide English material or an English translation;
9. for Developer Tools, include installation instructions, supported platforms, and a way to test without rebuilding.

## BOOTMUX mapping

### Codex

Codex was the implementation and execution engine for:

- the Go PTY/WebSocket Companion;
- the native SwiftUI/CoreBluetooth client;
- the ESP32-S3 BLE-to-native-USB-HID firmware;
- the ARM64 Lima VM harness;
- the bounded target-side Codex adapter;
- Judge Mode, tests, probes, and repair cycles.

### GPT-5.6

GPT-5.6 was the architecture, adversarial-review, and convergence layer for:

- the asymmetric physical-input and independently observed-output architecture;
- bounded protocol, queue, lifecycle, and overflow contracts;
- BLE queue-ownership root-cause analysis;
- HID Mirror path-binding review;
- evidence classes and public-claim boundaries;
- submission structure and closeout control.

### Human

The human owner selected the problem and hardware direction, operated the real devices, controlled authentication, accepted or rejected repairs, edited the final video, and owns every final public claim and submission action.

## Working-project boundary

The submission claim is intentionally bounded:

```text
physical input:
iPhone → BLE → ESP32-S3 → native USB HID → target

independently observed return:
target PTY / Codex → BOOTMUX Companion → local WebSocket → iPhone
```

The project does not treat a bridge acknowledgement as target output. Judge Mode is a review path and is not presented as physical BLE or USB HID evidence.

## Developer Tools test path

Judges can test without rebuilding the hardware stack:

- open `judge/index.html` locally for the standalone offline replay;
- use the packaged macOS arm64 Judge Mode;
- or run the Go Companion locally and open `/judge`.

Installation and platform details are in the root README and `judge/README.md`.

## Current closeout state

```yaml
registration:
  status: GREEN_OWNER_CONFIRMED
  submitter_type: INDIVIDUAL
  country: JAPAN
  category: DEVELOPER_TOOLS
primary_codex_thread: CONFIRMED
feedback_receipt:
  captured_privately: true
  entered_in_devpost: true
  public_session_id: false
codex_majority_core_work: COMPLETE
meaningful_gpt_5_6_evidence: RECORDED_PUBLICLY
license: MIT_GREEN
judge_mode: GREEN
iphone_to_ble_to_usb_hid: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
codex_installation_clean_arm64_vm: GREEN
bootmux_ready:
  direct_vm: PASS
  companion_codex_prompt: PASS
  physical_iphone_return: PASS
video:
  final_master_complete: true
  public_youtube_url_verified: PENDING
final_submission: NOT_CONFIRMED
production_ready: false
```

## Remaining external actions

- upload or finalize the video on YouTube;
- verify public visibility, sub-three-minute duration, audible narration, and the signed-out URL;
- confirm the narration explains the project, Codex, and GPT-5.6;
- place the final video URL in Devpost and the repository submission map;
- accept the terms and confirm successful final submission.

## Unresolved technical gates

These are not submission-package failures, but they remain outside the completed public claim:

- repeatable production-ready physical operation;
- physical selectable-copy and exact-paste acceptance;
- visible CLEAR acceptance;
- physical HID Mirror acceptance;
- Unicode HID and mouse support;
- full terminal emulation;
- complete offline target operation;
- continued post-bootstrap operation.

## Source index

- [Official Rules](https://openai.devpost.com/rules)
- [Official FAQ](https://openai.devpost.com/details/faqs)
- [Build Week overview](https://openai.devpost.com/)

Current repository status is maintained in [Build Week Status](submission/BUILD_WEEK_STATUS.md), [Final Checklist](submission/FINAL_CHECKLIST.md), and [Claim and Evidence Matrix](submission/CLAIM_EVIDENCE_MATRIX.md).