# BOOTMUX Next Implementation Task — Submission Spine

## Status

```yaml
previous_task:
  task_id: BOOTMUX-V0A-R3-TERMINAL-ERROR-SHUTDOWN-REPAIR
  status: GREEN
  final_head_sha: 2f9378f0d84ce0b3cb0caabdd9229a8ae7f0b2d4
current_task:
  task_id: BOOTMUX-BW0-BW2-SUBMISSION-SPINE
  implementation_status: COMPLETE
  gate_status: YELLOW_HUMAN_CONFIRMATION_PENDING
next_technical_task:
  task_id: BOOTMUX-V0B-IPHONE-TERMINAL-LOOP
  status: BLOCKED_PENDING_REGISTRATION_AND_PRIMARY_THREAD_CONFIRMATION
pull_request: 1
branch: agent/bootstrap-design-roadmap
```

This documentation-only task operationalizes the OpenAI Build Week submission requirements. It does not implement a new runtime feature. V0A Companion Core is complete and locally verified; V0B remains blocked until this submission spine is green.

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
