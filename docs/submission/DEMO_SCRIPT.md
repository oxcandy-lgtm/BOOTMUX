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

app_design_and_agent_loop:
  status: COMPLETE_LOCAL_EDIT
  duration_seconds: 28.233
  format: 1920x1080_16_9
  placement: IMMEDIATELY_AFTER_OPENING
  category: APP_DESIGN_TABS_LOGS_AND_AGENT_LOOP
  sequence:
    - SUBLIMINAL_DOG_FLASH
    - APP_LAUNCH_AND_VISUAL_DESIGN
    - TERMINAL_TAB
    - CODEX_TAB
    - DIAGNOSTICS_AND_LOG_CONTROLS
    - INPUT_UI
    - CODEX_BUILD_GPT56_REVIEW_HUMAN_TASTE_REPEAT
  subliminal_dog_retained: true
  english_narration: true
  english_burned_subtitles: true
  operation_callouts_separate_from_narration_subtitles: true
  final_loop_card: CODEX_BUILDS_GPT56_REVIEWS_HUMAN_TASTE_REPEAT
  final_message: FROM_FUNCTIONAL_TO_PERSONAL
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

completed_duration_seconds: 82.166
```

The app-design segment is intentionally placed directly after the opening. It introduces the product surface before the physical HID proof and already covers the rapid Codex / GPT-5.6 / human convergence loop. The subliminal dog remains only as a brief opening flash and is not presented as a product feature.

The HID SEND segment uses two consecutive views because only one camera was available. It must not be described as a synchronized dual-camera recording. The segment honestly demonstrates the phone-side operation followed by the observed physical terminal result.

## Recommended final allocation

```text
0:00.00–0:17.23  COMPLETE — dirty-display problem, ESP32-S3 reveal, BOOT GPT-5.6 / BOOTMUX opening.
0:17.23–0:45.47  COMPLETE — app design, tab switching, diagnostics/log controls, and Codex / GPT-5.6 / human iteration loop.
0:45.47–1:22.17  COMPLETE — HID SEND function test and physical terminal reflection.
1:22.17–1:40.00  REQUIRED — integrated physical path: TERM ON, bounded Codex prompt, BOOTMUX_READY returning to the iPhone.
1:40.00–1:49.00  REQUIRED IF CONFIRMED — select, copy, paste, and visible CLEAR feedback. Otherwise show Judge copy and label physical acceptance pending.
1:49.00–1:58.00  REQUIRED — asymmetric architecture: input uses BLE → ESP32-S3 → USB HID; terminal return uses PTY → Companion → local WebSocket → iPhone.
1:58.00–2:05.00  REQUIRED — no-rebuild Judge Mode, honest limitations, and closing line.
```

Recommended final duration: **125 seconds**.

```yaml
hard_limit_seconds: 180
recommended_final_seconds: 125
completed_seconds: 82.166
remaining_to_hard_limit_seconds: 97.834
remaining_recommended_seconds: 42.834
```

Do not fill the entire three-minute allowance. The remaining footage should be limited to the proof that is not already visible in the completed segments.

## Development-loop coverage

The completed app-design segment already presents the loop as:

```text
CODEX BUILDS
→ GPT-5.6 REVIEWS
→ HUMAN TASTE
→ REPEAT
```

This concise product-facing version is supported by the fuller project workflow:

```text
HUMAN GOAL + END
→ GPT-5.6 DECOMPOSES AND SETS CONTRACTS
→ CODEX IMPLEMENTS AND RUNS TESTS
→ GPT-5.6 REVIEWS CODE AND EVIDENCE
→ CODEX REPAIRS AND RE-VALIDATES
→ HUMAN PHYSICAL ACCEPTANCE
```

The final assembly must preserve the claim boundary: GPT-5.6 did not autonomously own the project, Codex did not perform physical acceptance, and the human selected the direction and accepted the physical result.

## Loop evidence that may appear visually

Use no more than three concise examples when any additional evidence card is needed:

1. `V0A R1–R3` — Codex implementation → GPT-5.6 lifecycle review → Codex repair and stress validation.
2. `BLE QUEUE ROOT FIX` — GPT-5.6 found unsafe queue ownership → Codex replaced it with bounded POD frames.
3. `R4R1 MIRROR PATH FIX` — GPT-5.6 found path-binding and stale-writer risk → Codex unified the VM path and made overflow fail closed.

These examples establish that the loop changed real implementation behavior; they are stronger than showing a generic chat screenshot.

## Explanations that must survive the final edit

1. **Problem and product:** BOOTMUX creates a path to AI before the target computer is ready to run AI normally.
2. **Product surface:** the app exposes terminal, Codex, diagnostics/log controls, connection state, and manual input without requiring a full-size keyboard.
3. **Physical input proof:** iPhone committed text travels through BLE and ESP32-S3 and reaches the target as USB HID keyboard input.
4. **End-to-end Codex proof:** the target-side Codex path returns the exact `BOOTMUX_READY` marker to the iPhone.
5. **Asymmetric transport boundary:** input is physical BLE / ESP32-S3 / USB HID; current terminal return is Companion / local WebSocket, not an ESP32-S3 return channel.
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
  status: IN_PROGRESS_THREE_SEGMENTS_COMPLETE
  final_master: false
  public_upload: false
  completed_segments: 3
  completed_duration_seconds: 82.166
  remaining_recommended_seconds: 42.834
  next_required_clip: INTEGRATED_CODEX_BOOTMUX_READY_RETURN
  app_design_and_agent_loop_segment: COMPLETE
```

## Owner acceptance gates

```text
selectable_copy: PENDING_OWNER_CONFIRMATION
clear_visible_feedback: PENDING_OWNER_CONFIRMATION
repeatability: PENDING
```

Do not mark these gates passed from a local unit test, Judge replay, or an edited reconstruction.
