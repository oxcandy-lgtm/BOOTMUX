# ESP32-S3 Provisional Hardware Profile

Inventory date: 2026-07-20 (read-only Mac USB inspection)

```yaml
physical_ports:
  - COM
  - USB
connector_type: USB-C x2
currently_connected: USB
exact_board_model: UNRESOLVED
chip: ESP32-S3
chip_revision: v0.2
flash_size: 16MB
psram: 8MB
native_usb_enumeration: COMPOSITE_USB_SEEN_HID_NOT_CONFIRMED
firmware_upload: PASS_COM_SIDE
```

Observed from the connected USB device, with serial values intentionally omitted:

```yaml
usb_product_name: USB Single Serial
usb_vendor_id: "0x1A86"
usb_product_id: "0x55D3"
serial_candidate: present_but_not_recorded
usb_uart_bridge:
  family: WCH_CH343_class
  evidence:
    product: USB Single Serial
    vid: "0x1A86"
    pid: "0x55D3"
  confidence: high
```

The current read-only inventory sees the separate USB-side Espressif composite device (VID `0x303A`, PID `0x1001`) but no confirmed HID keyboard interface. No COM device is currently available for the R3 descriptor build, so that build has not been flashed. The COM-side WCH CH343-class inventory remains recorded above as the expected upload role. RGB LED observation remains human-reported as blinking.

The read-only chip and flash probes identified ESP32-S3 revision v0.2, 16MB flash, and 8MB PSRAM. A local flash backup was attempted before the earlier V1 write but esptool stalled after chip detection; the attempt was stopped and no backup artifact is treated as valid. Bluetooth addresses, USB serial numbers, private hostnames, and account data are intentionally excluded. Exact board model, connector mapping, native USB HID enumeration, and real BLE measurements remain unresolved until the board marking and both physical connectors are verified.
