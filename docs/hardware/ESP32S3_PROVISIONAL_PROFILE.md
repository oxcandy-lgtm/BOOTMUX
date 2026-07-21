# ESP32-S3 Provisional Hardware Profile

This file combines the original read-only USB inventory with the later bounded physical evidence. The exact retail board model remains unresolved; that uncertainty does not erase the later owner-observed native USB HID ASCII path.

## Original read-only inventory — 2026-07-20

```yaml
physical_ports:
  - COM
  - USB
connector_type: USB-C_x2
connected_during_inventory: USB
exact_board_model: UNRESOLVED
chip: ESP32-S3
chip_revision: v0.2
flash_size: 16MB
psram: 8MB
native_usb_enumeration_at_inventory: COMPOSITE_USB_SEEN_HID_NOT_CONFIRMED
firmware_upload_at_inventory: PASS_COM_SIDE
```

The COM-side inventory identified a WCH CH343-class USB-to-UART bridge:

```yaml
usb_product_name: USB Single Serial
usb_vendor_id: "0x1A86"
usb_product_id: "0x55D3"
serial_candidate: present_but_not_recorded
```

The separate USB-side Espressif composite device was seen during that inventory, but the read-only snapshot did not by itself prove a HID keyboard interface. A local flash-backup attempt stalled after chip detection and was stopped; no backup artifact is treated as valid.

## Later reconciliation

```yaml
firmware_build: PASS
firmware_upload: PASS
ble_open_and_short_operation: OWNER_OBSERVED
native_usb_hid_ascii_delivery: OWNER_OBSERVED_BOUNDED_PATH
physical_BOOTMUX_READY_return: OWNER_OBSERVED_SEPARATE_RETURN_PATH
exact_board_model: UNRESOLVED
full_control_acceptance: PENDING
reconnect_and_repeatability: PENDING
production_ready: false
```

The later physical evidence is recorded in:

- [`../evidence/V1_PHYSICAL_KEYBOARD_PATH.md`](../evidence/V1_PHYSICAL_KEYBOARD_PATH.md)
- [`../evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md`](../evidence/V2_V6_CODEX_PHYSICAL_RETURN_PROGRESS.md)
- [`../submission/CLAIM_EVIDENCE_MATRIX.md`](../submission/CLAIM_EVIDENCE_MATRIX.md)

## Port and evidence boundary

- use the board's COM connector for the documented upload/debug role;
- use the native USB connector for the target-side USB HID path;
- the exact connector mapping must still be checked on an unfamiliar replacement board;
- an upload log or USB enumeration alone is not physical target-output evidence;
- the public claim remains printable ASCII only, with no mouse, Unicode HID, full controls, or repeatability claim.

Bluetooth addresses, USB serial numbers, local paths, hostnames, credentials, and account data are intentionally excluded.