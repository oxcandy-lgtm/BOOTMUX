# BOOTMUX Demo Production Record

The final narrated demo master is complete according to the owner. This file preserves the public-safe production intent and final verification requirements without pretending that YouTube publication or Devpost submission has already been confirmed.

## Final production state

```yaml
final_submission_video:
  status: FINAL_MASTER_COMPLETE_OWNER_REPORTED
  final_master: true
  public_upload: PENDING_CONFIRMATION
  public_url_in_repository: false
  hard_limit_seconds: 180
  duration_under_limit: PENDING_FINAL_PLAYBACK_VERIFICATION
  english_narration: true
  burned_subtitles: true
  final_privacy_review: PENDING_FINAL_PLAYBACK_VERIFICATION
```

## Required story coverage

The final edit is intended to preserve all of the following:

1. **Problem:** normal AI, SSH, or remote-development access may not exist during bootstrap or recovery.
2. **Product:** BOOTMUX creates a physical first mile from an iPhone through BLE and ESP32-S3 USB HID.
3. **Observed return:** target PTY and Codex output returns independently through the Companion and local WebSocket.
4. **Physical proof:** bounded ASCII input reaches the target through the physical path.
5. **Codex proof:** a real target-side Codex interaction returns the exact marker `BOOTMUX_READY` to the iPhone.
6. **Codex contribution:** Codex implemented and repaired the Go Companion, SwiftUI client, firmware, VM harness, adapter, Judge Mode, tests, and probes.
7. **GPT-5.6 contribution:** GPT-5.6 shaped the architecture, bounded contracts, root-cause analysis, evidence boundaries, and repair loop.
8. **Human contribution:** the human selected the product direction, operated the hardware, judged physical evidence, edited the final video, and owns every public claim.
9. **Judge path:** reviewers can inspect the terminal-and-copy experience without rebuilding or owning the hardware.
10. **Honest limits:** no production-readiness, repeatability, Unicode HID, mouse, full terminal emulator, or complete offline claim.

## Architecture wording that must remain clear

```text
Physical input:
iPhone → BLE → ESP32-S3 → native USB HID → target

Observed return:
target PTY / Codex → Companion → local WebSocket → iPhone
```

The two paths must not be described as if BLE or USB HID acknowledgement alone proved that the target processed the command.

## Development-loop wording

Product-facing version:

```text
CODEX BUILDS
→ GPT-5.6 REVIEWS
→ HUMAN JUDGMENT
→ REPEAT
```

Full evidence-backed version:

```text
HUMAN GOAL + END CONDITION
→ GPT-5.6 DECOMPOSES AND SETS BOUNDED CONTRACTS
→ CODEX IMPLEMENTS, RUNS TESTS, AND RETURNS EVIDENCE
→ GPT-5.6 REVIEWS CODE, FAILURES, AND PROOF BOUNDARIES
→ CODEX REPAIRS AND RE-VALIDATES
→ HUMAN PHYSICAL ACCEPTANCE OR AN EXPLICIT UNRESOLVED GATE
```

## Strong implementation examples

The strongest concrete examples of the Codex/GPT-5.6 loop are:

1. **Companion lifecycle repairs:** Codex implementation → GPT-5.6 lifecycle review → Codex stress-tested repair.
2. **BLE queue root fix:** GPT-5.6 identified unsafe ownership in raw-copied non-trivial queue objects → Codex replaced them with bounded POD-owned frames.
3. **HID Mirror path fix:** GPT-5.6 identified path-binding and stale-writer risk → Codex unified the path and changed overflow handling to fail closed.

## Closing line

Preferred:

> **The physical first mile for Codex. Built by Codex, hardened with GPT-5.6, and closed by human proof.**

## Final playback checklist

Before public upload, the owner must verify:

- total duration is below three minutes;
- narration is intelligible throughout;
- Codex and GPT-5.6 are both explained explicitly;
- music never competes with narration;
- subtitles match the spoken claims;
- no private endpoint, credential, account name, device identifier, or unredacted terminal history is visible;
- the physical and Judge Mode evidence are labeled separately;
- the YouTube upload is Public and opens while signed out.

## Unresolved physical acceptance gates

```yaml
selectable_copy: PENDING_OWNER_CONFIRMATION
clear_visible_feedback: PENDING_OWNER_CONFIRMATION
physical_hid_mirror: PENDING_OWNER_CONFIRMATION
repeatability: PENDING
```

These gates cannot be passed from Judge Replay, unit tests, or edited footage alone.
