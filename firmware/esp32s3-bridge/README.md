# BOOTMUX ESP32-S3 V1 Keyboard Bridge

This is the bounded Build Week physical keyboard path: BLE GATT input to a native USB HID keyboard. It uses the official Arduino-ESP32 framework through the pinned PlatformIO environment.

```yaml
framework: Arduino-ESP32
platform: espressif32@6.9.0
board_target: esp32-s3-devkitc-1
usb_device_name: BOOTMUX Keyboard
ble_device_name: BOOTMUX Keyboard
keyboard_layout: US_ANSI_QWERTY
character_scope: printable_ASCII
service_uuid: 7c1b0001-4b4f-4d55-9a01-42584d583101
rx_write_uuid: 7c1b0002-4b4f-4d55-9a01-42584d583102
tx_notify_uuid: 7c1b0003-4b4f-4d55-9a01-42584d583103
```

The wire format is the core keyboard profile of [BMX1](../../docs/protocol/BMX1.md), with `OPEN`, batched `TEXT`, typed `CTRL`, and ACK/ERR notifications.

`OPEN` returns `OPENED` only after the new session is accepted. Text is committed in logical messages instead of one BLE transaction per character. Duplicate `(session, sequence)` operations return `DUPLICATE` and are not applied twice. Incomplete reassembly is discarded on disconnect or timeout.

`STOP` releases all keys, clears pending data, latches output disabled, and returns `STOPPED`. `RESUME` releases all keys, clears the latch, and returns `RESUMED`. Every control and parser-error path returns toward a neutral keyboard report. Unicode outside printable ASCII is intentionally unsupported for this gate.

## Build

From the repository root, using the project-local PlatformIO environment:

```sh
.tools/platformio-venv/bin/pio run -d firmware/esp32s3-bridge
```

The native USB HID proof requires the ESP32-S3 native USB connector, not the COM upload connector. No device identifier, serial, BLE address, MAC address, credential, or private host path belongs in committed evidence.

## Evidence boundary

The repository supports an owner-observed bounded ASCII physical path. It does not claim full control-key acceptance, reconnect repeatability, Unicode HID, mouse support, production readiness, or independently observed target output from a BLE acknowledgement alone.