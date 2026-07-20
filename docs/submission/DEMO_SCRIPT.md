# BOOTMUX Demo Script

Target duration: 2 minutes 40 seconds or less. Use voice narration. Do not include private endpoints, credentials, device identifiers, or third-party music.

## Recording order for the current physical path

1. Show the completed dirty-display problem reenactment and ESP32-S3 reveal.
2. Show the BOOTMUX architecture diagram.
3. Show Companion live Judge Mode.
4. Show `BOOTMUX_JUDGE` observed PTY output.
5. Show the physical iPhone path and `BOOTMUX_READY` return.
6. Select and copy the output if owner confirmation is available.
7. Show standalone Judge Replay Mode.
8. Show the Codex/GPT-5.6 evidence ledger.
9. State the honest limitations, including pending copy confirmation, CLEAR feedback, repeatability, and production readiness.

## Current physical demo allocation

```text
0:00–0:17  COMPLETED — dirty-display problem reenactment, ESP32-S3 reveal, English narration/subtitles, and BOOT GPT-5.6 / BOOTMUX title treatment.
0:17–0:35  Architecture diagram and the asymmetric input/output boundary.
0:35–0:55  Companion live Judge Mode.
0:55–1:10  BOOTMUX_JUDGE observed PTY output.
1:10–1:25  Physical iPhone path: bounded ASCII HID input and BOOTMUX_READY return.
1:25–1:40  Select-and-copy moment if owner confirmation is available; otherwise label it pending.
1:40–1:55  Standalone Judge Replay Mode.
1:55–2:10  Codex/GPT-5.6 evidence ledger.
2:10–2:35  Honest limitations: copy/CLEAR confirmation and repeatability pending; no Unicode HID, mouse, full terminal emulator, or production claim.
```

Editing target: 155 seconds maximum, with voice narration and fewer than 300
spoken words. The 17-second opening segment is edited and narrated. It is an
opening segment only and still requires final submission-level privacy review.
The owner-recorded `HID_SEND_PHYSICAL_15S` clip is approximately 15 seconds and
remains pending privacy review. Remaining product clips are not yet assembled,
the final narrated master is not complete, and public video upload is pending.

## Video production state

```yaml
opening_segment:
  status: COMPLETE_LOCAL_EDIT
  duration_seconds: 17
  english_narration: true
  english_burned_subtitles: true
  screen_effects: true
  esp32s3_reveal_title: BOOT_GPT_5_6
  final_privacy_review: pending
final_submission_video:
  status: IN_PROGRESS
  final_master: false
  public_upload: false
```

## Owner acceptance gates

```text
selectable_copy: PENDING_OWNER_CONFIRMATION
clear_visible_feedback: PENDING_OWNER_CONFIRMATION
repeatability: PENDING
```

Do not mark these gates passed from a local unit test or from the Judge replay.
