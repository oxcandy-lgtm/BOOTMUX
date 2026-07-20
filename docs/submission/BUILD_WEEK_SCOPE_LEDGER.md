# Build Week Scope Ledger

This ledger separates pre-existing project material from work attributed to the submission period without guessing dates that are not recorded here.

```yaml
scope:
  pre_existing:
    - BOOTMUX concept and exploratory architecture
    - architecture and roadmap documents created before the submission-period implementation history
  submission_period:
    - V0A Companion Core implementation and its repair iterations
    - Build Week submission documentation and public-safe evidence ledgers
    - Devpost draft copy and story structure
  unknown_or_not_claimed:
    - exact calendar dates for individual pre-existing materials
    - unrecorded hardware, iPhone, BLE, USB HID, or Codex implementation work
commits:
  V0A_initial: 7854781a69d6bc0d93e7759ba8aa467e5b0e2a04
  V0A_R1_final: 6099662d7e146ba250381df33b3aea14a995e3e7
  V0A_R2: 9ff5766e17276df367f8a1219ebc992eab82765b
  V0A_R3: 2f9378f0d84ce0b3cb0caabdd9229a8ae7f0b2d4
  devpost_draft: bf74c4d5d30f41d0a7df69f93a0929d6588e0416
```

## Evidence mapping

| Scope item | Evidence | Claim boundary |
| --- | --- | --- |
| V0A Companion Core | `companion/` and V0A commits above | local target-side proof only |
| V0A R1–R3 repairs | the R1, R2, and R3 commits above | lifecycle and contract repair evidence, not hardware proof |
| Devpost draft | `docs/submission/DEVPOST_COPY_AND_STORY_DRAFT.md` at `devpost_draft` | working draft, not final submission copy |
| iPhone/BLE/USB HID/Codex | no implementation commit recorded in this ledger | not claimed as complete |

No private session transcript, account data, private path, hostname, device serial, or guessed date is part of this public ledger.
