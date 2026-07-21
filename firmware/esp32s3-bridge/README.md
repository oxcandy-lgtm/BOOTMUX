# BOOTMUX ESP32-S3 V1 keyboard bridge

This is the bounded V1 physical keyboard path: BLE GATT input to native USB HID keyboard. It uses the official Arduino-ESP32 framework through the pinned PlatformIO environment.

```yaml
framework: Arduino-ESP32
platform: espressif32@6.9.0
board_target: esp32-s3-devkitc-1
layout: US_ANSI_QWERTY
character_scope: printable_ASCII
service_uuid: 7c1b0001-4b4f-4d55-9a01-42584d583101
```

The wire format is `BMX1` with `OPEN`, batched `TEXT`, typed `CTRL`, and ACK/ERR notifications. `OPEN` returns `OPENED` only after the new session is accepted. Text is committed in logical messages and is not written one character per BLE transaction. Duplicate `(session, sequence)` operations are acknowledged as `DUPLICATE`; incomplete reassembly is discarded on disconnect or timeout.

`STOP` releases all keys, clears pending data, latches output disabled, and returns `STOPPED`. `RESUME` releases all keys, clears the latch, and returns `RESUMED`. `OPEN` does not clear the STOP latch. Every control and parser error path returns to a neutral keyboard report. Unicode outside printable ASCII is intentionally unsupported for this gate.

Build locally with the project-local PlatformIO environment:

```sh
.tools/platformio-venv/bin/pio run -d firmware/esp32s3-bridge
```

The native USB HID proof requires the ESP32-S3 native USB connector, not the COM upload connector. No device identifier, serial, MAC, or private path belongs in committed evidence.
