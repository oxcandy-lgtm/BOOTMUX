# BMX1 BLE Protocol

BMX1 is the bounded, ASCII-framed BLE protocol shared by the iPhone client and BOOTMUX ESP32-S3 firmware.

The **core keyboard profile** is used by `firmware/esp32s3-bridge/`. The independent `firmware/esp32s3-router-spike/` preserves the core profile and adds experimental Wi-Fi and proxy messages. Those network extensions are not part of the Build Week physical-input claim.

## GATT contract

```yaml
device_names:
  keyboard_bridge: BOOTMUX Keyboard
  router_spike: BOOTMUX Bridge
service_uuid: 7c1b0001-4b4f-4d55-9a01-42584d583101
rx_write_uuid: 7c1b0002-4b4f-4d55-9a01-42584d583102
tx_notify_uuid: 7c1b0003-4b4f-4d55-9a01-42584d583103
```

The iPhone writes frames to RX and receives acknowledgements, errors, and optional network state through TX notifications.

## Core keyboard frames

Frames are ASCII, pipe-delimited, and begin with `BMX1`.

```text
BMX1|OPEN|<session>
BMX1|TEXT|<session>|<sequence>|<part>|<total>|<escaped-payload>
BMX1|CTRL|<session>|<sequence>|ENTER
BMX1|CTRL|<session>|<sequence>|BACKSPACE
BMX1|CTRL|<session>|<sequence>|CTRL_C
BMX1|CTRL|<session>|<sequence>|STOP
BMX1|CTRL|<session>|<sequence>|RESUME
```

Core responses:

```text
BMX1|ACK|<session>|0|OPENED
BMX1|ACK|<session>|<sequence>|APPLIED
BMX1|ACK|<session>|<sequence>|DUPLICATE
BMX1|ACK|<session>|<sequence>|STOPPED
BMX1|ACK|<session>|<sequence>|RESUMED
BMX1|ERR|<session>|<sequence>|<public-safe-error-code>
```

`TEXT` payload escaping uses backslash sequences for `|`, `\`, newline, and carriage return. The current public HID path accepts printable ASCII only; the iPhone rejects unsupported HID text before creating an operation.

## Core bounds and semantics

```yaml
committed_text_max_bytes: 512
text_parts_max: 32
receiver_frame_storage_bytes: 520
frame_queue_entries: 32
reassembly_timeout_seconds: 2
completed_sequence_cache_entries: 16
keyboard_layout: US_ANSI_QWERTY
```

- `OPEN` installs a fresh session and returns `OPENED` only after it is accepted.
- A `(session, sequence)` that was already completed returns `DUPLICATE` and is not applied twice.
- Incomplete reassembly is discarded on timeout, disconnect, or replacement by a different operation.
- `STOP` releases all keys, clears pending data, latches output disabled, and returns `STOPPED`.
- `RESUME` releases all keys, clears the stop latch, and returns `RESUMED`.
- Parser, disconnect, and control paths return the keyboard toward a neutral report.
- A BLE acknowledgement is not independently observed target output.

## Experimental router extensions

The router spike adds these request frames:

```text
BMX1|WIFI|<session>|<sequence>|<part>|<total>|<base64-json>
BMX1|WIFI_STATUS|<session>|<sequence>|STATUS
BMX1|WIFI_CLEAR|<session>|<sequence>|CLEAR
BMX1|PROXY_STATUS|<session>|<sequence>|STATUS
```

Network and proxy notifications:

```text
BMX1|NET|<session>|<sequence>|WIFI_IDLE
BMX1|NET|<session>|<sequence>|WIFI_CONNECTING
BMX1|NET|<session>|<sequence>|WIFI_ONLINE
BMX1|NET|<session>|<sequence>|WIFI_AUTH_FAILED
BMX1|NET|<session>|<sequence>|WIFI_AP_NOT_FOUND
BMX1|NET|<session>|<sequence>|WIFI_NO_IP
BMX1|NET|<session>|<sequence>|WIFI_DISCONNECTED
BMX1|NET|<session>|<sequence>|WIFI_CLEARED
BMX1|PROXY_STATUS|<session>|<sequence>|PROXY_OFFLINE
BMX1|PROXY_STATUS|<session>|<sequence>|PROXY_READY
BMX1|PROXY_STATUS|<session>|<sequence>|PROXY_READY|ENDPOINT=<private-ipv4>:3128|EPOCH=<decimal>
BMX1|PROXY_STATUS|<session>|<sequence>|PROXY_ERROR
```

Experimental Wi-Fi bounds:

```yaml
wifi_parts_max: 16
wifi_decoded_json_max_bytes: 192
ssid_max_bytes: 32
password_bytes: 0_or_8_to_63
wifi_command_queue_entries: 2
connection_deadline_seconds: 15
maximum_attempts: 3
storage: RAM_ONLY
```

Credentials are base64 transport payloads, not encryption. They must travel only over the operator-controlled local BLE link, remain in bounded transient buffers on the spike, and never appear in source, logs, fixtures, screenshots, recordings, or public evidence.

## Claim boundary

The Build Week public claim uses the core keyboard profile only. Wi-Fi provisioning, USB Ethernet, CONNECT proxying, and complete recovery routing remain experimental and must not be inferred from the bounded BLE-to-USB-HID evidence.