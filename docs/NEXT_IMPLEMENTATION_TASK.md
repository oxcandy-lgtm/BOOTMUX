# BOOTMUX Current Next Task

This file records the current post-integration task. The previous pre-merge task contract is preserved in Git history and is no longer an instruction for the repository.

```yaml
status_as_of: 2026-07-22_JST
integration_pr:
  number: 1
  state: MERGED
  merge_commit: 024e384ff60956a5be9abfb45d056d6b2d6ff150
current_branch_of_record: main
submission_package: GREEN_WITH_EXTERNAL_CLOSEOUT_PENDING
```

## Immediate external closeout

The repository-side Build Week package is complete. The remaining organizer-facing actions are:

1. publish the final narrated video to YouTube;
2. verify public visibility, duration, narration, and the signed-out link;
3. place the final video URL in Devpost and the repository submission map;
4. accept the Devpost terms and confirm the final submission.

The real `/feedback` Session ID remains private and must not be committed.

## Next technical task after submission

```yaml
task_id: BOOTMUX-POST-BUILD-WEEK-PHYSICAL-ACCEPTANCE
scope:
  - repeatable physical BLE and USB HID run
  - physical selectable-copy and exact-paste acceptance
  - visible CLEAR acceptance
  - physical HID Mirror acceptance
  - reproducible evidence receipt
not_in_scope:
  - production-readiness claim
  - Unicode HID
  - mouse support
  - full terminal emulation
```

Current public claims remain governed by [Claim and Evidence Matrix](submission/CLAIM_EVIDENCE_MATRIX.md) and [Build Week Status](submission/BUILD_WEEK_STATUS.md).