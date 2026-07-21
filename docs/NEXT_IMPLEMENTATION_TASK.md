# BOOTMUX Next Implementation Task — Submission Spine

## Status

```yaml
previous_task:
  task_id: BOOTMUX-S81-SUBMISSION-CLOSEOUT
  status: YELLOW_SUBMISSION_READY
  final_head_sha: 66c99c35d7ea714e9a013319ed3ac7d871715031
current_task:
  task_id: BOOTMUX-R4-PHYSICAL-DEMO-REPEATABILITY-HID-MIRROR-VIDEO
  implementation_status: IMPLEMENTED_LOCAL_MIRROR_AND_USABILITY_CONTROLS_PHYSICAL_COPY_CLEAR_REPEATABILITY_PENDING
  feature_development: BOUNDED_DEMO_SCOPE_ONLY
  submission_baseline_preserved: true
next_technical_task:
  task_id: BOOTMUX-R4-PHYSICAL-DEMO-OWNER-ACCEPTANCE
  status: BLOCKED_PENDING_OWNER_COPY_CLEAR_AND_REPEATABILITY_CONFIRMATION
pull_request: 1
branch: agent/bootstrap-design-roadmap
```

This task is limited to a repeatable physical-demo slice. The Submission Closeout baseline remains preserved. The implementation adds bounded iPhone usability controls, an ASCII fail-fast boundary, and a read-only HID mirror beside the existing PTY path. It does not claim Unicode HID, mouse/trackpad, a full terminal emulator, production readiness, or a completed owner acceptance receipt.

## Required artifacts

- `docs/submission/BUILD_WEEK_STATUS.md`
- `docs/submission/BUILD_WEEK_SCOPE_LEDGER.md`
- `docs/submission/CODEX_GPT56_EVIDENCE_LEDGER.md`
- `docs/submission/CLAIM_EVIDENCE_MATRIX.md`
- README sections for scope, Codex, GPT-5.6, human decisions, and pre-existing work
- an append-only update to existing Draft PR #1

## Non-negotiable boundaries

- Do not read, search, create, edit, comment on, or call APIs for GitHub Issues.
- Do not create, inspect, run, rerun, or depend on GitHub Actions; do not add `.github/workflows/`.
- Do not choose or add a repository license in this task.
- Do not run `/feedback` or publish a real Session ID, account data, private paths, hostnames, device serials, or screenshots.
- Do not implement V0B, iPhone, BLE, USB HID, Codex bootstrap, or hardware features here.
- Keep PR #1 Draft, open, and unmerged; do not create another PR, merge, mark ready, force-push, or push to `main`.

## Local acceptance

Run the Companion tests, race tests, vet, Markdown/path and public-safety checks, `git diff --check`, complete diff inspection, commit/push, and exact remote-head verification. The final report must distinguish implemented evidence from human confirmation still pending.
