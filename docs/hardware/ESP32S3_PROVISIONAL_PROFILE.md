# ESP32-S3 Provisional Hardware Profile

Inventory date: 2026-07-20 (read-only Mac USB inspection)

```yaml
physical_ports:
  - COM
  - USB
connector_type: USB-C x2
currently_connected: COM
exact_board_model: UNRESOLVED
chip: ESP32-S3
chip_revision: v0.2
flash_size: 16MB
psram: 8MB
native_usb_enumeration: PENDING_USB_CONNECTOR_PROBE
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

The inventory is consistent with the currently connected COM / USB-to-UART role. The bridge chipset is not declared from product strings alone. The V1 firmware uploaded successfully through the COM side with verified write hashes. The separate USB connector remains the expected native ESP32-S3 USB / HID role, but it is not the currently connected path and native enumeration is still pending. RGB LED observation remains human-reported as blinking.

The read-only chip and flash probes identified ESP32-S3 revision v0.2, 16MB flash, and 8MB PSRAM. A local flash backup was attempted before any write but esptool stalled after chip detection; the attempt was stopped, no backup artifact is treated as valid, and no firmware write has occurred. Bluetooth addresses, USB serial numbers, private hostnames, and account data are intentionally excluded. Exact board model, connector mapping, native USB HID enumeration, and real BLE measurements remain unresolved until the board marking and both physical connectors are verified.
