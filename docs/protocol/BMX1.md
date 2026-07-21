# BMX1 BLE protocol — R7B

R7B adds BLE Wi-Fi provisioning while preserving the R7A USB HID and USB
Ethernet interfaces. The ESP-IDF runtime advertises as `BOOTMUX Bridge` and
uses bounded RX, notification, and Wi-Fi command queues.

## Frames

Frames are ASCII, pipe-delimited, and begin with `BMX1`.

```text
BMX1|OPEN|<session>
BMX1|WIFI|<session>|<sequence>|<part>|<total>|<base64-json>
BMX1|WIFI_STATUS|<session>|<sequence>
BMX1|WIFI_CLEAR|<session>|<sequence>
BMX1|CTRL|<session>|<sequence>|STOP|RESUME|ENTER|BACKSPACE|CTRL_C
```

The provisioning JSON contains `ssid` and `password` and is base64-encoded
before transmission. The password may be empty for an open network, otherwise
it must be 8–63 bytes. SSIDs are limited to 32 bytes. This document contains
no real network credentials.

## Bounded behavior

BLE frames are limited to 520 bytes and the RX queue holds 32 frames. Wi-Fi
reassembly is limited to 16 parts, with a 512-byte transport payload bound
and a two-second reassembly timeout. The Wi-Fi worker queue holds two
commands. When a queue or payload bound is exceeded, the device sends a safe
error such as `wifi_queue_overflow` or `oversized_wifi_payload` when
notification is still possible, then rejects the work. It never silently
truncates output or credentials. If notification is unavailable, the
operation remains failed closed locally.

Credentials are copied only into bounded transient buffers, configured with
RAM-only Wi-Fi storage, and zeroed after use. No credential is persisted by
this runtime or emitted to logs.

## Network state

The TX characteristic reports `NET` markers including `WIFI_IDLE`,
`WIFI_CONNECTING`, `WIFI_ONLINE`, `WIFI_AUTH_FAILED`, `WIFI_AP_NOT_FOUND`,
`WIFI_NO_IP`, `WIFI_DISCONNECTED`, and `WIFI_CLEARED`. R7B does not claim a
DHCP/DNS/NAPT/TCP proxy or a completed end-to-end iPhone uplink.
