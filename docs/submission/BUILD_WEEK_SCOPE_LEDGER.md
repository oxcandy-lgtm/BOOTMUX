# Build Week Scope Ledger

This public ledger separates work attributed to the Build Week submission period from any pre-existing material without inventing dates or private history.

```yaml
scope:
  pre_existing_confirmed:
    - none established by public repository evidence
  submission_period:
    - BOOTMUX repository initialization
    - architecture, protocols, roadmap, and public-safety boundaries
    - Go Companion Core and lifecycle/overflow repairs
    - native SwiftUI and CoreBluetooth iPhone client
    - ESP32-S3 BLE-to-native-USB-HID bridge firmware
    - clean ARM64 Lima VM harness and official Codex CLI installation path
    - bounded target-side Codex adapter and probes
    - physical bounded ASCII keyboard-path evidence
    - physical BOOTMUX_READY return evidence
    - HID Mirror implementation and local tests
    - standalone, packaged, and live local Judge Mode
    - MIT license, setup instructions, supported platforms, and security guidance
    - Codex and GPT-5.6 evidence ledger and development-loop documentation
    - canonical Project Story and Devpost submission map
    - narrated demo production and final master
  unresolved_private_history:
    - whether any uncommitted private concept or note existed before the submission period
```

## Selected implementation history

The repository and PR history remain the authoritative source for exact SHAs. The following public mappings identify major delivery slices without claiming that every intermediate repair is reproduced here.

| Slice | Repository evidence | Public boundary |
| --- | --- | --- |
| Companion Core | `companion/`, `docs/COMPANION_PROTOCOL_V1.md`, PR repair history | bounded local target-side PTY/WebSocket Companion |
| iPhone client | `iphone/`, `iphone/README.md` | native implementation; physical claims remain separately evidenced |
| BLE and USB HID bridge | `firmware/esp32s3-bridge/`, `docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md` | bounded owner-observed ASCII path only |
| Clean VM and Codex install | `vm/`, `docs/evidence/V3_CODEX_CLEAN_INSTALL.md` | clean ARM64 Lima VM installation and bounded probes |
| Codex adapter | `companion/codex.go`, Companion tests, VM run scripts | bounded one-shot local adapter, not a production agent service |
| Physical Codex return | `docs/evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md`, `docs/evidence/V6_INTEGRATED_DEMO.md` | owner-observed `BOOTMUX_READY` return; repeatability/copy remain separate |
| HID Mirror | `companion/mirror.go`, tests, VM launchers, evidence records | implemented and locally tested; physical acceptance pending |
| Judge Mode | `judge/`, `companion/judge/`, `dist/bootmux-judge-macos-arm64/` | no-build terminal/session/copy experience; not physical BLE/HID proof |
| Tool-use evidence | `docs/submission/CODEX_GPT56_EVIDENCE_LEDGER.md` | public-safe mapping of Codex, GPT-5.6, and human roles |
| Submission package | `README.md`, `docs/PROJECT_STORY.md`, `docs/submission/` | public project and submission materials |

## Evidence rules

- Code presence is not automatically physical proof.
- A BLE or firmware acknowledgement is not independently observed target output.
- Judge Replay proves only the replayed terminal/session/copy experience.
- Owner-observed physical claims must remain bounded to the recorded hardware slice.
- Private `/feedback` identifiers, credentials, local endpoints, account details, device identifiers, and signing material do not belong in this ledger.
- Unknown private pre-history is left unresolved rather than guessed.

## Current final boundary

Supported as public submission-period work:

- major software, firmware, VM, Judge Mode, evidence, and submission layers were built or materially repaired during the repository development period;
- Codex served as the implementation and execution engine;
- GPT-5.6 served as architecture, adversarial review, root-cause analysis, and convergence control;
- the human selected the product direction, performed hardware setup and observations, edited the video, and approved every final claim.

Not inferred from this ledger:

- exact hours saved;
- autonomous ownership by either AI system;
- production readiness;
- completion of unresolved physical acceptance gates;
- absence of any private idea before the public repository unless separately confirmed.
