# Build Week Scope Ledger

This ledger separates pre-existing project material from work attributed to the submission period without guessing dates that are not recorded here.

```yaml
scope:
  pre_existing_confirmed:
    - none currently established by public repository evidence
  submission_period:
    - BOOTMUX repository initialization
    - committed BOOTMUX architecture and roadmap
    - OpenAI Build Week requirements and compliance documents
    - V0A Companion Core implementation
    - V0A R1-R3 repairs
    - V0B iPhone Terminal Loop implementation
    - V0B R1 client runtime contract repairs
    - V0B R2 protocol-limit and Xcode-host repairs
    - submission ledgers
    - Devpost copy and story draft
  unresolved_pending_owner_confirmation:
    - whether any private BOOTMUX concept existed before 2026-07-13 09:00 PDT
commits:
  V0A_initial: 7854781a69d6bc0d93e7759ba8aa467e5b0e2a04
  V0A_R1_final: 6099662d7e146ba250381df33b3aea14a995e3e7
  V0A_R2: 9ff5766e17276df367f8a1219ebc992eab82765b
  V0A_R3: 2f9378f0d84ce0b3cb0caabdd9229a8ae7f0b2d4
  devpost_draft: bf74c4d5d30f41d0a7df69f93a0929d6588e0416
  V0B_implementation: 2d730a5a287166a889e26e0067f2d518327390d1
  V0B_R1_repair: d9746c818eabc31b8bc6bf50c44ecdcbd3dbf395
  V0B_R2_repair: f554b38a5e0c5218c98f0811b7b8667bd379a32e
```

## Evidence mapping

| Scope item | Evidence | Claim boundary |
| --- | --- | --- |
| V0A Companion Core | `companion/` and V0A commits above | local target-side proof only |
| V0A R1–R3 repairs | the R1, R2, and R3 commits above | lifecycle and contract repair evidence, not hardware proof |
| Devpost draft | `docs/submission/DEVPOST_COPY_AND_STORY_DRAFT.md` at `devpost_draft` | working draft, not final submission copy |
| BLE/USB HID/Codex | no implementation commit recorded in this ledger | not claimed as complete |
| V0B iPhone Terminal Loop | `iphone/` at `V0B_implementation` | implementation is recorded; physical iPhone proof is not claimed |
| V0B R1 client runtime contract | `iphone/` at `V0B_R1_repair` | normal exit, bounded output, CRLF, injected transport, lifecycle, and project contract repairs; physical proof remains unclaimed |
| V0B R2 protocol and Xcode contract | `iphone/` at `V0B_R2_repair` | single protocol limits, bounded input/close timeout, finalization, selection helper, and standard test-host project structure; Xcode/physical proof pending |

No private session transcript, account data, private path, hostname, device serial, or guessed date is part of this public ledger.
