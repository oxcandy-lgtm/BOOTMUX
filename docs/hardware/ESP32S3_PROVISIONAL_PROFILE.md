# ESP32-S3 Provisional Hardware Profile

Inventory date: 2026-07-20 (read-only Mac USB inspection)

```yaml
physical_ports:
  - COM
  - USB
connector_type: USB-C x2
currently_connected: COM
exact_board_model: UNRESOLVED
```

Observed from the connected USB device, with serial values intentionally omitted:

```yaml
usb_product_name: USB Single Serial
usb_vendor_id: "0x1A86"
usb_product_id: "0x55D3"
serial_candidate: present_but_not_recorded
```

The inventory is consistent with the currently connected COM / USB-to-UART role. The bridge chipset is not declared from product strings alone. The separate USB connector remains the expected native ESP32-S3 USB / future HID role, but native enumeration was not established by this read-only check. RGB LED observation remains human-reported as blinking.

No firmware write, erase, reset, or port-occupying process was performed. Bluetooth addresses, USB serial numbers, private hostnames, and account data are intentionally excluded. Exact board model, connector mapping, native USB HID enumeration, and real BLE measurements remain unresolved until the board marking and both physical connectors are verified.
