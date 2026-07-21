# Claim and Evidence Matrix

Only claims with both evidence and an allowed public copy are publishable. This matrix and [Canonical Project Story](../PROJECT_STORY.md) are the paired public sources of truth. Submission wrappers such as [Devpost Submission Map](DEVPOST_FINAL_DRAFT.md) must not diverge from them.

| Claim key | Status | Evidence | Public copy allowed | Remaining gate |
| --- | --- | --- | --- | --- |
| V0A_companion_core | GREEN | `companion/`, local tests, and V0A R3 history | true | none for V0A target-side scope |
| judge_mode_terminal_copy | GREEN | `judge/index.html`, packaged local Companion `/judge`, and offline replay | true | final human/demo review |
| ble_transport_stability | GREEN | `docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md`, firmware POD queue repair, and observed `OPENED` plus eight `APPLIED` acknowledgements without disconnect | true for the bounded short-operation transport path | full V1 controls, reconnect, duplicate, and stability receipt |
| iphone_live_terminal | PHYSICAL_BOOTMUX_READY_OBSERVED_COPY_PENDING | owner-supplied physical receipt plus `docs/evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md` | false | selectable copy, CLEAR feedback, repeatability |
| real_ble_input | BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED | `docs/evidence/V1_PHYSICAL_KEYBOARD_PATH.md` and owner-supplied physical receipt | false | repeatable acceptance and explicit ASCII boundary |
| real_usb_hid | GREEN | prior public-safe native USB HID and ASCII delivery receipt, plus current firmware upload | true for the observed ASCII keyboard path | full V1 control and stability acceptance |
| mouse_support | NOT_IMPLEMENTED | no mouse implementation or proof | false | implement and demonstrate |
| offline_target_operation | NOT_PROVEN | no offline target run evidence | false | reproducible offline demonstration |
| codex_installation | GREEN_IN_CLEAN_ARM64_VM | clean ARM64 Lima VM installation and direct probe | true for bounded demo wording | continued post-bootstrap operation |
| BOOTMUX_READY | DIRECT_VM_COMPANION_AND_PHYSICAL_RETURN | docs/evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md | true for observed bounded path | selectable copy, repeatability |
| continued_post_boot_use | NOT_PROVEN | no post-bootstrap operation evidence | false | repeatable continued-use demonstration |

The V0A public claim is limited to a locally verified target-side Companion Core. It does not imply completion of the physical or Codex bootstrap path.

Current boundary: the physical ASCII BLE/USB-HID and BOOTMUX_READY return
are observed, while copy, CLEAR feedback, repeatability, Unicode HID, mouse
support, full terminal emulation, and production readiness are not claimed.
