# BOOTMUX V0B iPhone Terminal Loop

This dependency-free SwiftUI application implements the V0 software terminal loop and the bounded V1 BLE input bridge:

```text
iPhone native input → local WebSocket → BOOTMUX Companion → PTY → observed output → selectable copyable text
```

It deliberately does not implement mouse input, Codex installation, cloud services, background operation, or a full terminal emulator. Production terminal transport is `URLSessionWebSocketTask`; the BLE bridge uses system CoreBluetooth and there are no external runtime packages.

The V1 bridge is now implemented with CoreBluetooth and the pinned `BMX1` protocol, but physical iPhone-to-BLE-to-ESP32-S3-to-USB-HID proof remains pending. The WebSocket terminal path remains separate from `SEND VIA HID`.

## Build

Open `BOOTMUX.xcodeproj` in Xcode with an iOS SDK. Signing settings are not committed and `DEVELOPMENT_TEAM` is empty.

Unsigned validation, when Xcode is available, must set the override on the command line, for example `xcodebuild -project BOOTMUX.xcodeproj -scheme BOOTMUX -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO build`.

## Local run

Start the Companion on a trusted local network:

```sh
cd companion
go run . -addr 0.0.0.0:8765 -allow-remote
```

In the app, enter `ws://<trusted-local-host>:8765/v1/terminal`, tap CONNECT, then send `echo BOOTMUX_V0` and tap ENTER. Only observed PTY output is added to the selectable terminal view. The owner-observed physical path is bounded ASCII and includes a `BOOTMUX_READY` return; selectable copy, CLEAR feedback, and repeatability remain pending.

## Bounds and safety

- terminal history is capped at 131072 UTF-8 bytes and evicts oldest text;
- output is coalesced for UI updates on a 50ms interval;
- CSI, OSC, and simple control sequences are removed by a streaming sanitizer;
- stale generations and session IDs are rejected;
- disconnect cancels the WebSocket receive loop and pending UI flush;
- connected disconnect sends a best-effort protocol `close` with a 150ms bound;
- inactive/background scene phases disconnect without automatic reconnect;
- local-network ATS is enabled without `NSAllowsArbitraryLoads`.
