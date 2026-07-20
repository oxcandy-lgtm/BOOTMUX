# BOOTMUX Companion V0A

The Companion is a loopback-first, non-daemon Go executable. Each WebSocket connection creates an isolated PTY session running the explicitly configured shell. The versioned endpoint is `GET /v1/terminal`; client messages and observed PTY output are distinct protocol types.

```sh
cd companion
go build ./...
go test ./...
go run . -addr 127.0.0.1:8765
go run -tags probe . -endpoint ws://127.0.0.1:8765/v1/terminal
```

Output is bounded by a fixed PTY chunk queue, accumulated-byte limit, and WebSocket outbound queue. Overflow never silently truncates: the Companion sends `output_overflow` when the bounded queues permit, then closes the session fail-closed. The 35ms `FlushInterval` is a maximum latency from the first pending byte: additional bytes do not reset it. Newline or byte-threshold flushes stop the timer when pending is empty and re-arm it only for remaining bytes.

The listener is loopback-only by default. A non-loopback bind requires the explicit `-allow-remote` flag, and browser Origins are accepted only when they match the request host; Origin-less native clients remain allowed. Remote binding must be protected by an external network boundary and must not be exposed directly to an untrusted network.

The client event loop enqueues input and interrupt requests into a fixed input queue; a dedicated PTY writer preserves order. `control:interrupt` is ordered after earlier queued text and writes byte `0x03` to the PTY, allowing the terminal line discipline to signal the foreground process group. Terminal errors use a per-message writer ACK; queue failure, writer failure, ACK timeout, or client disconnect all fail closed. Session stop closes the PTY to unblock a stuck writer, kills the child/process group when available, and waits for process, reader, input writer, and output writer completion before returning. On restricted Unix fallback paths, only direct-child and PTY cleanup is claimed; process-group descendant cleanup requires Setpgid support. This local probe does not prove the deferred iPhone, BLE, USB HID, or ESP32-S3 paths.

When the official Codex executable is installed inside a demo VM, the same endpoint also accepts bounded one-shot `codex_prompt`, `codex_cancel`, and `codex_new_session` messages. Only one Codex process may run at a time; prompts are limited to 8 KiB, output to 128 KiB, and execution to 180 seconds. Codex output is a separate observed event stream and never becomes PTY input. The adapter does not authenticate, dump environment variables, expose credentials, or claim that a host-side Codex run occurred inside the VM.
