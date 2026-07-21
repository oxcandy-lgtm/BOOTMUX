# BOOTMUX R7B BLE Wi-Fi provisioning runtime

This project is an independent ESP-IDF/TinyUSB spike. It does not replace or
modify `firmware/esp32s3-bridge/`.

R7B preserves the R7A USB composite path:

- product string: `BOOTMUX Bridge`
- HID keyboard interface
- USB Ethernet interface using the initial NCM descriptor candidate
- the R7A bounded ASCII HID probe remains compile-time opt-in

NCM is an implementation candidate, not a BOOTMUX product claim. The Mac
enumeration result decides whether the next spike uses NCM or a native
macOS-compatible ECM/TinyUSB NET configuration. R7B adds an ESP-IDF NimBLE
runtime and a dedicated Wi-Fi STA worker; the existing Arduino project in
`firmware/esp32s3-bridge/` remains independent and is not replaced. R7B does
not claim DHCP, DNS, NAPT, TCP proxying, or a completed iPhone network UI.

Protocol details are in [`docs/protocol/BMX1.md`](../../docs/protocol/BMX1.md).

Bounds and failure behavior are part of the contract:

- BLE input frames are bounded to 520 bytes and queued in a fixed 32-entry queue.
- Wi-Fi commands use a fixed two-entry queue; a full queue returns
  `BMX1|ERR|<session>|<sequence>|wifi_queue_overflow` when notification is
  possible. No output or credential is silently truncated.
- Wi-Fi payloads are base64-encoded JSON, decoded to at most 192 bytes, with an
  SSID limit of 32 bytes and a password limit of 63 bytes.
- Reassembly is bounded to 16 parts and expires after two seconds. Connection
  attempts have a 15-second deadline and at most three attempts before
  `WIFI_NO_IP`.
- Credentials are erased from transient buffers and are not written to NVS.

This is a software implementation gate. Physical BLE/Wi-Fi acceptance still
requires flashing the built image and owner-supplied real network credentials;
credentials must not be placed in source, logs, or evidence.

## Build and flash

```sh
.tools/platformio-venv/bin/pio run -d firmware/esp32s3-router-spike
.tools/platformio-venv/bin/pio run -d firmware/esp32s3-router-spike -t upload
```

On the current ARM64 validation host, the PlatformIO ESP-IDF package's
bundled CMake is not executable, so the verified build used the same ESP-IDF
project with a native ARM64 CMake. This is a host-tool limitation, not a
physical enumeration result. A board must be placed in its documented download
mode before any write operation; a normal USB serial enumeration alone is not
proof that the R7A image was uploaded.

Use the board's native `USB` connector for the device-side enumeration test.
The existing `COM` path remains the upload/debug fallback. Do not report a
GREEN gate from a compile alone: Mac USB enumeration, ASCII HID input,
unplug/replug re-enumeration, and a clean serial log without panic/watchdog
reset are required.

Expected serial markers:

```text
BOOTMUX_ROUTER_SPIKE_STARTED
BOOTMUX_USB_ETHERNET_READY
BOOTMUX_HID_READY
```

No network address, credential, serial number, BLE address, or private host
path belongs in this spike's evidence.
