# BOOTMUX V0B iPhone Terminal Loop

This dependency-free SwiftUI application implements the V0 software terminal loop:

```text
iPhone native input → local WebSocket → BOOTMUX Companion → PTY → observed output → selectable copyable text
```

It deliberately does not implement BLE, ESP32-S3, USB HID, mouse input, Codex installation, cloud services, background operation, or a full terminal emulator. Production transport is `URLSessionWebSocketTask`; there are no external packages or runtime dependencies.

## Build

Open `BOOTMUX.xcodeproj` in Xcode with an iOS SDK. Signing settings are not committed and `DEVELOPMENT_TEAM` is empty.

Unsigned validation, when Xcode is available, must set the override on the command line, for example `xcodebuild -project BOOTMUX.xcodeproj -scheme BOOTMUX -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO build`.

## Local run

Start the Companion on a trusted local network:

```sh
cd companion
go run . -addr 0.0.0.0:8765 -allow-remote
```

In the app, enter `ws://<trusted-local-host>:8765/v1/terminal`, tap CONNECT, then send `echo BOOTMUX_V0` and tap ENTER. Only observed PTY output is added to the selectable terminal view. Physical iPhone proof is still pending.

## Bounds and safety

- terminal history is capped at 131072 UTF-8 bytes and evicts oldest text;
- output is coalesced for UI updates on a 50ms interval;
- CSI, OSC, and simple control sequences are removed by a streaming sanitizer;
- stale generations and session IDs are rejected;
- disconnect cancels the WebSocket receive loop and pending UI flush;
- connected disconnect sends a best-effort protocol `close` with a 150ms bound;
- inactive/background scene phases disconnect without automatic reconnect;
- local-network ATS is enabled without `NSAllowsArbitraryLoads`.
