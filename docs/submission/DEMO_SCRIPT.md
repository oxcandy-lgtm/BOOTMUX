# BOOTMUX Demo Script

Hard limit: 3 minutes. Recommended final master: approximately 2 minutes 5 seconds. Use voice narration. Do not include private endpoints, credentials, device identifiers, local account names, unredacted terminal history, or third-party music.

## Completed edited segments

```yaml
opening_segment:
  status: COMPLETE_LOCAL_EDIT
  duration_seconds: 17.233
  format: 1920x1080_16_9
  english_narration: true
  english_burned_subtitles: true
  screen_effects: true
  esp32s3_reveal_title: BOOT_GPT_5_6
  final_privacy_review: pending

hid_send_function_test:
  status: COMPLETE_LOCAL_EDIT
  duration_seconds: 36.700
  format: 1920x1080_16_9
  category: HID_SEND_FUNCTION_TEST_AND_TERMINAL_REFLECTION
  sequence:
    - BLE_CONNECT
    - ENTER_X2
    - TYPE_HELLO
    - HID_SEND
    - PHYSICAL_TERMINAL_REFLECTION
  operation_callouts_separate_from_narration_subtitles: true
  english_narration: true
  english_burned_subtitles: true
  technical_card: BLE_BATCH_TO_ESP32S3_TO_USB_HID
  public_safe_redaction: applied
  final_privacy_review: pending

completed_duration_seconds: 53.933
```

The HID SEND segment uses two consecutive views because only one camera was available. It must not be described as a synchronized dual-camera recording. The segment honestly demonstrates the phone-side operation followed by the observed physical terminal result.

## Recommended final allocation

```text
0:00.00–0:17.23  COMPLETE — dirty-display problem, ESP32-S3 reveal, BOOT GPT-5.6 / BOOTMUX opening.
0:17.23–0:53.93  COMPLETE — HID SEND function test and physical terminal reflection.
0:53.93–1:15.00  REQUIRED — integrated physical path: TERM ON, bounded Codex prompt, BOOTMUX_READY returning to the iPhone.
1:15.00–1:27.00  REQUIRED IF CONFIRMED — select, copy, paste, and visible CLEAR feedback. Otherwise show Judge copy and label physical acceptance pending.
1:27.00–1:39.00  REQUIRED — asymmetric architecture: input uses BLE → ESP32-S3 → USB HID; terminal return uses PTY → Companion → local WebSocket → iPhone.
1:39.00–1:55.00  REQUIRED — rapid development loop: Human END condition → GPT-5.6 contracts/review → Codex implementation/tests → GPT-5.6 FIX → Codex re-validation → human physical acceptance.
1:55.00–2:05.00  REQUIRED — no-rebuild Judge Mode, honest limitations, and closing line.
```

Recommended final duration: **125 seconds**.

```yaml
hard_limit_seconds: 180
recommended_final_seconds: 125
completed_seconds: 53.933
remaining_to_hard_limit_seconds: 126.067
remaining_recommended_seconds: 71.067
```

Do not fill the entire three-minute allowance. The remaining footage should be limited to the proof that is not already visible in the completed segments.

## Development-loop segment

This segment should use a simple animated or static six-stage flow rather than scrolling through long source files:

```text
HUMAN GOAL + END
→ GPT-5.6 DECOMPOSES AND SETS CONTRACTS
→ CODEX IMPLEMENTS AND RUNS TESTS
→ GPT-5.6 REVIEWS CODE AND EVIDENCE
→ CODEX REPAIRS AND RE-VALIDATES
→ HUMAN PHYSICAL ACCEPTANCE
```

Suggested narration, approximately 38–43 spoken words:

> BOOTMUX was not generated in one prompt. I set the goal and physical direction. GPT-5.6 repeatedly converted that intent into bounded contracts and reviewed the results. Codex implemented and tested them across Go, SwiftUI, ESP32-S3 firmware, and an ARM64 VM until the physical demo worked.

Optional final sentence when pacing permits:

> Codex supplied implementation velocity; GPT-5.6 supplied verification pressure; human judgment kept the loop aimed at END.

Do not imply that GPT-5.6 autonomously owned the project, that Codex performed the physical acceptance, or that an exact hour count was measured.

## Loop evidence that may appear visually

Use no more than three concise examples:

1. `V0A R1–R3` — Codex implementation → GPT-5.6 lifecycle review → Codex repair and stress validation.
2. `BLE QUEUE ROOT FIX` — GPT-5.6 found unsafe queue ownership → Codex replaced it with bounded POD frames.
3. `R4R1 MIRROR PATH FIX` — GPT-5.6 found path-binding and stale-writer risk → Codex unified the VM path and made overflow fail closed.

These examples establish that the loop changed real implementation behavior; they are stronger than showing a generic chat screenshot.

## Explanations that must survive the final edit

1. **Problem and product:** BOOTMUX creates a path to AI before the target computer is ready to run AI normally.
2. **Physical input proof:** iPhone committed text travels through BLE and ESP32-S3 and reaches the target as USB HID keyboard input.
3. **End-to-end Codex proof:** the target-side Codex path returns the exact `BOOTMUX_READY` marker to the iPhone.
4. **Asymmetric transport boundary:** input is physical BLE / ESP32-S3 / USB HID; current terminal return is Companion / local WebSocket, not an ESP32-S3 return channel.
5. **Why manual input matters:** AI is the primary setup path, but a human can still type without carrying a full-size keyboard.
6. **Rapid convergence loop:** human direction was decomposed and reviewed by GPT-5.6, implemented and executed by Codex, repaired through repeated review cycles, and closed by human physical acceptance.
7. **Codex and GPT-5.6 contribution:** Codex built major implementation slices; GPT-5.6 shaped architecture, bounded contracts, repair analysis, claim safety, and submission structure.
8. **Honest limitations:** bounded ASCII keyboard path, no mouse or Unicode HID claim, no full terminal emulator, no production-readiness claim, and no repeatability/copy/CLEAR claim until owner-confirmed.

Everything else is optional and should be removed before any of these eight points are compressed beyond comprehension.

## Closing line

Preferred:

> **The physical first mile for Codex. Built through a Codex and GPT-5.6 development loop, and closed by human proof.**

Short fallback:

> **Built by Codex. Hardened with GPT-5.6. Proven by a human.**

## Final production state

```yaml
final_submission_video:
  status: IN_PROGRESS_TWO_SEGMENTS_COMPLETE
  final_master: false
  public_upload: false
  completed_segments: 2
  completed_duration_seconds: 53.933
  remaining_recommended_seconds: 71.067
  next_required_clip: INTEGRATED_CODEX_BOOTMUX_READY_RETURN
  required_concept_segment: CODEX_GPT56_CONVERGENCE_LOOP
```

## Owner acceptance gates

```text
selectable_copy: PENDING_OWNER_CONFIRMATION
clear_visible_feedback: PENDING_OWNER_CONFIRMATION
repeatability: PENDING
```

Do not mark these gates passed from a local unit test, Judge replay, or an edited reconstruction.
