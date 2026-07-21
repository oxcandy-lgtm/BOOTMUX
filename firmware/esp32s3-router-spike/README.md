# BOOTMUX R7A USB Ethernet feasibility spike

This project is an independent ESP-IDF/TinyUSB spike. It does not replace or
modify `firmware/esp32s3-bridge/`.

The first gate is only USB composite enumeration:

- product string: `BOOTMUX Bridge`
- HID keyboard interface
- USB Ethernet interface using the initial NCM descriptor candidate
- one bounded ASCII HID probe (`B`), emitted only after the device is mounted

NCM is an implementation candidate, not a BOOTMUX product claim. The Mac
enumeration result decides whether the next spike uses NCM or a native
macOS-compatible ECM/TinyUSB NET configuration. No Wi-Fi, BLE provisioning,
DHCP, DNS, NAPT, TCP proxy, or iPhone UI is included at R7A.

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
