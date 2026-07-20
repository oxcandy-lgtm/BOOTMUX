# BOOTMUX Companion V0A

The Companion is a loopback-first, non-daemon Go executable. Each WebSocket connection creates an isolated PTY session running the explicitly configured shell. The versioned endpoint is `GET /v1/terminal`; client messages and observed PTY output are distinct protocol types.

```sh
cd companion
go build ./...
go test ./...
go run . -addr 127.0.0.1:8765
go run -tags probe . -endpoint ws://127.0.0.1:8765/v1/terminal
```

Output is bounded by a fixed PTY chunk queue, accumulated-byte limit, and WebSocket outbound queue. Overflow never silently truncates: the Companion sends `output_overflow` when the bounded queues permit, then closes the session fail-closed. Output is aggregated and flushed on newline, a 35ms timer, a 512-byte threshold, or process exit; incomplete UTF-8 is held across chunks and replaced deterministically at exit.

The listener is loopback-only by default. A non-loopback bind requires the explicit `-allow-remote` flag, and browser Origins are accepted only when they match the request host; Origin-less native clients remain allowed. Remote binding must be protected by an external network boundary and must not be exposed directly to an untrusted network.

The interrupt control writes byte `0x03` to the PTY, allowing the terminal line discipline to signal the foreground process group. The Companion waits for and reaps the child before completing the session. This local probe does not prove the deferred iPhone, BLE, USB HID, or ESP32-S3 paths.
