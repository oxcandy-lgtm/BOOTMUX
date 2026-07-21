# BOOTMUX iPhone client

This dependency-free SwiftUI application implements two deliberately separate paths:

```text
Terminal path:
iPhone → local WebSocket → BOOTMUX Companion → PTY
       ← independently observed bounded terminal output

Physical input path:
iPhone committed text → CoreBluetooth → ESP32-S3 → native USB HID → target
```

It deliberately does not implement mouse input, cloud services, background operation, or a full terminal emulator. Production terminal transport uses `URLSessionWebSocketTask`; the BLE bridge uses system CoreBluetooth; there are no external iPhone runtime packages.

The current public evidence supports an owner-observed bounded ASCII BLE-to-ESP32-S3-to-USB-HID path and a physical `BOOTMUX_READY` return to the iPhone. Physical selectable-copy, visible CLEAR feedback, HID Mirror acceptance, and repeatability remain separate unresolved gates.

## Requirements

- Xcode with an iOS SDK
- iOS 17 or later
- local signing for a physical device
- a trusted local network for the Companion terminal path
- an ESP32-S3 with native USB device support for the physical HID path

## Build

Open `BOOTMUX.xcodeproj` in Xcode. Signing settings are not committed and `DEVELOPMENT_TEAM` remains empty.

Unsigned simulator validation, when Xcode is available:

```sh
xcodebuild \
  -project BOOTMUX.xcodeproj \
  -scheme BOOTMUX \
  -sdk iphonesimulator \
  CODE_SIGNING_ALLOWED=NO \
  build
```

## Run the local terminal path

Start the Companion on a trusted local network from the repository root:

```sh
cd companion
go run . -addr 0.0.0.0:8765 -allow-remote
```

In the app:

1. enter `ws://<trusted-local-host>:8765/v1/terminal`;
2. tap **CONNECT**;
3. send `echo BOOTMUX_V0`;
4. use the dedicated ENTER control;
5. verify that only independently observed PTY output appears in the terminal view.

Do not expose the remote-bind mode directly to an untrusted network. The Companion requires explicit `-allow-remote`; the surrounding trusted network boundary remains the operator's responsibility.

## Run the physical input path

1. build and upload the firmware under `firmware/esp32s3-bridge/`;
2. connect the ESP32-S3 native USB connector to the target computer;
3. connect the iPhone to the advertised BOOTMUX BLE service;
4. send bounded printable ASCII through the HID controls;
5. observe the target independently.

The current firmware scope is US ANSI QWERTY printable ASCII plus typed controls. Unicode HID and mouse support are not implemented.

## Experimental router controls

The Settings screen retains a visible **Network Bridge — Experimental** section for the independent `firmware/esp32s3-router-spike/` research path. That router experiment uses a different RX/TX characteristic profile from the demonstrated core keyboard bridge.

In the Build Week core iPhone build:

- the app connects to the demonstrated core keyboard profile;
- router Wi-Fi and proxy controls are visibly labeled experimental;
- router mutation controls are disabled fail-closed;
- router framing and parsing code remains available for isolated research and tests;
- Wi-Fi, USB Ethernet, proxy routing, and complete recovery routing are not part of the current public claim.

## Bounds and safety

- terminal history is capped at 131072 UTF-8 bytes and evicts oldest text;
- output is coalesced for UI updates on a 50 ms interval;
- CSI, OSC, and simple control sequences are removed by a streaming sanitizer;
- stale generations and session IDs are rejected;
- disconnect cancels the WebSocket receive loop and pending UI flush;
- connected disconnect sends a best-effort protocol `close` with a 150 ms bound;
- background scene phases disconnect without automatic reconnect;
- local-network ATS is enabled without `NSAllowsArbitraryLoads`;
- sent BLE/HID input is not promoted into observed terminal output.

See the [Claim and Evidence Matrix](../docs/submission/CLAIM_EVIDENCE_MATRIX.md) for the exact public boundary.