# BOOTMUX R7B BLE Wi-Fi provisioning runtime

This project is an independent ESP-IDF/TinyUSB spike. It does not replace or
modify `firmware/esp32s3-bridge/`.

## Host-network safety boundary

The normal build is now **USB HID-only**. Plugging the ESP32-S3 into a Mac must
not enumerate a USB Ethernet interface, start a DHCP exchange, publish a DNS
server, or offer a default route. The USB product string is
`BOOTMUX Keyboard Safe` and the serial string is `BOOTMUX-HID-SAFE`.

This is intentional. The earlier router-spike build always exposed CDC-NCM and
created a DHCP-server netif at `10.77.0.1`. A host could install that interface
as an active network service and prefer it over Wi-Fi even though the router
path was still experimental. The safe profile removes that control-plane side
effect while preserving USB HID, BLE, and the S3's own RAM-only Wi-Fi STA
runtime.

R7B bounds remain part of the contract:

- BLE input frames are bounded to 520 bytes and queued in a fixed 32-entry queue.
- Wi-Fi commands use a fixed two-entry queue; a full queue returns
  `BMX1|ERR|<session>|<sequence>|wifi_queue_overflow` when notification is
  possible. No output or credential is silently truncated.
- Wi-Fi payloads are base64-encoded JSON, decoded to at most 192 bytes, with an
  SSID limit of 32 bytes and a password limit of 63 bytes.
- Reassembly is bounded to 16 parts and expires after two seconds. Connection
  attempts have a 15-second deadline and at most three attempts before
  `WIFI_NO_IP`.
- Credentials are erased from transient buffers, use RAM-only Wi-Fi storage,
  and are not written to NVS.

Protocol details are in [`docs/protocol/BMX1.md`](../../docs/protocol/BMX1.md).

## Safe build and flash

The default `sdkconfig.defaults` selects TinyUSB network mode `None` and leaves
`CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL` disabled.

```sh
.tools/platformio-venv/bin/pio run -d firmware/esp32s3-router-spike
.tools/platformio-venv/bin/pio run -d firmware/esp32s3-router-spike -t upload
```

Expected safe serial marker:

```text
BOOTMUX_USB_NETWORK_SAFE_OFF
```

On macOS, the USB device must appear as a keyboard/HID device only. A new
`USB Ethernet`, NCM, ECM, or RNDIS network service is a failed safety gate.

## Explicit USB-network experiment

The old USB router path is retained only as an opt-in research profile. Build it
with `sdkconfig.usb-network.defaults` instead of the normal defaults. Do not use
this profile for ordinary BOOTMUX keyboard operation.

For a native ESP-IDF build, start from a clean sdkconfig and select the explicit
profile:

```sh
rm -f firmware/esp32s3-router-spike/sdkconfig
idf.py \
  -C firmware/esp32s3-router-spike \
  -D SDKCONFIG_DEFAULTS=sdkconfig.usb-network.defaults \
  reconfigure build
```

The experimental interface:

- uses CDC-NCM;
- has S3 address `10.77.0.1/24`;
- does **not** run a DHCP server;
- has no configured gateway;
- does not provide DNS;
- requires the Mac to use a manually assigned `10.77.0.x/24` address;
- requires destination-scoped routes rather than a default route.

A USB-network experiment is not GREEN until the Mac's default route, DNS, and
Wi-Fi association are byte-for-byte unchanged before and after attachment.

## Recover a Mac affected by the previous build

Keep the affected S3 attached long enough for the script to identify the active
`10.77.0.0/24` interface, then run:

```sh
scripts/macos/recover-bootmux-usb-network.sh --apply
```

After it reports PASS, unplug the old firmware or flash the safe image. The
script only targets an interface in `10.77.0.0/24`, disables the associated
macOS network service, removes a `10.77.0.1` default route if present, renews
the Wi-Fi DHCP lease, and toggles Wi-Fi once. It does not delete saved Wi-Fi
credentials.

## Physical validation boundary

A compile is not a physical result. Before GREEN:

- flash the safe image to the actual ESP32-S3 DevKitC;
- connect the native USB port to the user's Mac;
- verify no USB network interface or service is created;
- verify the existing L11 Wi-Fi association remains connected;
- compare default route and DNS state before/after;
- unplug/replug at least three times;
- confirm clean logs without panic, watchdog, or brownout reset.

Use the board's `COM` connector as the upload/debug fallback when available.
No real network credential, serial number, BLE address, or private host path
belongs in evidence.
