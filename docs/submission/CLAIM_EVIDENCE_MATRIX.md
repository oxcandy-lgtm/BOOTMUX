# Claim and Evidence Matrix

Only claims with both evidence and an allowed public copy are publishable. This matrix and [Canonical Project Story](../PROJECT_STORY.md) are the paired public sources of truth. Submission wrappers such as [Devpost Submission Map](DEVPOST_FINAL_DRAFT.md) must not diverge from them.

| Claim key | Status | Evidence | Public copy allowed | Remaining gate |
| --- | --- | --- | --- | --- |
| `companion_core` | GREEN | `companion/`, protocol docs, local tests, race tests, vet, builds, and V0A repair history | true for the bounded target-side Companion scope | none for the declared Companion scope |
| `judge_mode_terminal_copy` | GREEN | `judge/index.html`, packaged macOS arm64 Companion, and live local `/judge` path | true | final signed-out/public-link review |
| `iphone_client_implementation` | GREEN_IMPLEMENTED | `iphone/` SwiftUI/CoreBluetooth implementation and tests | true as an implementation claim | broader device/platform validation |
| `iphone_live_terminal` | PHYSICAL_BOOTMUX_READY_OBSERVED_COPY_PENDING | owner-supplied physical receipt plus `docs/evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md` | true for the owner-observed `BOOTMUX_READY` return; false for physical copy/CLEAR acceptance | selectable copy, visible CLEAR, and repeatability |
| `ble_transport_stability` | GREEN_BOUNDED_SHORT_OPERATION | `docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md`, firmware POD queue repair, and observed `OPENED` plus eight `APPLIED` acknowledgements without disconnect | true for the bounded short-operation transport path | reconnect, duplicate, longer-duration, and repeatability receipt |
| `real_ble_input` | BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED | `docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md` and owner-supplied physical receipt | true for the bounded owner-observed ASCII path | repeatable acceptance and explicit ASCII boundary |
| `real_usb_hid` | GREEN_OBSERVED_ASCII_KEYBOARD_PATH | public-safe native USB HID and ASCII delivery receipt plus current firmware | true for the observed bounded ASCII keyboard path | full control and repeatability acceptance |
| `codex_installation` | GREEN_IN_CLEAN_ARM64_VM | clean ARM64 Lima VM installation, verification scripts, and direct probes | true for the bounded clean-VM claim | continued post-bootstrap operation |
| `codex_adapter` | GREEN_BOUNDED_LOCAL | `companion/codex.go`, tests, VM harness, and production Companion probe | true for the declared bounded one-shot adapter | broader lifecycle and packaging validation |
| `BOOTMUX_READY` | DIRECT_VM_COMPANION_AND_PHYSICAL_RETURN | `docs/evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md` and integrated owner observation | true for the observed bounded path | repeatability and physical copy acceptance |
| `hid_mirror` | CODE_GREEN_PHYSICAL_CONFIRMATION_PENDING | `companion/mirror.go`, tests, launcher/path repairs, and evidence notes | true only as implemented and locally tested; false as a physical proof | physical HID Mirror acceptance |
| `mouse_support` | NOT_IMPLEMENTED | no mouse implementation or proof | false | implement and demonstrate |
| `unicode_hid` | NOT_IMPLEMENTED | no Unicode HID implementation or proof | false | implement and demonstrate |
| `offline_target_operation` | NOT_PROVEN | no complete offline target run evidence | false | reproducible offline target demonstration |
| `continued_post_boot_use` | NOT_PROVEN | no repeatable post-bootstrap operation evidence | false | repeatable continued-use demonstration |
| `production_readiness` | NOT_CLAIMED | bounded Build Week prototype and explicit limitations | false | product hardening, repeatability, packaging, and broader validation |

## Current public boundary

Publicly supportable:

- bounded owner-observed physical ASCII BLE and native USB HID input;
- independently observed physical `BOOTMUX_READY` return to the iPhone;
- clean ARM64 VM installation and bounded Codex probes;
- implemented native iPhone client, Go Companion, firmware, and Judge Mode;
- Judge Mode terminal, session, selection, and copy behavior;
- specific Codex and GPT-5.6 contributions documented in the evidence ledger.

Not publicly supportable as completed:

- repeatable production-ready physical operation;
- physical selectable-copy or visible CLEAR acceptance;
- physical HID Mirror acceptance;
- Unicode HID or mouse support;
- full terminal emulation;
- complete offline target operation;
- continued post-bootstrap operation.

Judge Replay, local unit tests, and edited footage cannot independently promote a physical claim to GREEN.
