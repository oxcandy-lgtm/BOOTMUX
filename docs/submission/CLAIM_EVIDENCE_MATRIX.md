# Claim and Evidence Matrix

Only claims with both evidence and an allowed public copy are publishable. This matrix must remain consistent with [Devpost Copy and Story Draft](DEVPOST_COPY_AND_STORY_DRAFT.md).

| Claim key | Status | Evidence | Public copy allowed | Remaining gate |
| --- | --- | --- | --- | --- |
| V0A_companion_core | GREEN | `companion/`, local tests, and V0A R3 history | true | none for V0A target-side scope |
| iphone_live_terminal | IMPLEMENTED_AWAITING_PHYSICAL_PROOF | `iphone/` and V0B implementation commit; no physical acceptance receipt | false | physical iPhone connection, observed marker, native copy/paste |
| real_ble_input | NOT_PROVEN | no physical BLE evidence | false | real iPhone-to-BLE-to-device run |
| real_usb_hid | NOT_PROVEN | no native USB HID enumeration evidence | false | board-level enumeration and input proof |
| mouse_support | NOT_IMPLEMENTED | no mouse implementation or proof | false | implement and demonstrate |
| offline_target_operation | NOT_PROVEN | no offline target run evidence | false | reproducible offline demonstration |
| codex_installation | NOT_IMPLEMENTED | no Codex installation proof | false | clean-target installation evidence |
| BOOTMUX_READY | NOT_PROVEN | no V1/V4 marker run | false | end-to-end target and iPhone proof |
| continued_post_boot_use | NOT_PROVEN | no post-bootstrap operation evidence | false | repeatable continued-use demonstration |

The V0A public claim is limited to a locally verified target-side Companion Core. It does not imply completion of the physical or Codex bootstrap path.
