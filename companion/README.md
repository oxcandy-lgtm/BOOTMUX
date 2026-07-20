# BOOTMUX Companion V0A

The Companion is a loopback-first, non-daemon Go executable. Each WebSocket connection creates an isolated PTY session running the explicitly configured shell. The versioned endpoint is `GET /v1/terminal`; client messages and observed PTY output are distinct protocol types.

```sh
cd companion
go build ./...
go test ./...
go run . -addr 127.0.0.1:8765
go run -tags probe . -endpoint ws://127.0.0.1:8765/v1/terminal
```

Output is bounded and batched on newline, a short interval, a byte threshold, or process exit. This local probe does not prove the deferred iPhone, BLE, USB HID, or ESP32-S3 paths.
