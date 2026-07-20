# Companion Protocol V1

Endpoint: `GET /v1/terminal` over WebSocket. Every connection owns one fresh opaque `session_id`; output from another session is never reused.

Client messages are versioned JSON:

```json
{"v":1,"type":"input_text","session_id":"opaque","text":"..."}
{"v":1,"type":"control","session_id":"opaque","control":"interrupt"}
{"v":1,"type":"close","session_id":"opaque"}
```

Server messages distinguish observed PTY output from input:

```json
{"v":1,"type":"hello","session_id":"opaque"}
{"v":1,"type":"output","session_id":"opaque","stream":"pty","text":"..."}
{"v":1,"type":"exit","session_id":"opaque","exit_code":0}
{"v":1,"type":"error","session_id":"opaque","code":"...","message":"public-safe"}
```

The implementation bounds WebSocket messages at 16 KiB, JSON messages at 12 KiB, and `input_text` at 8 KiB. PTY chunks, the chunk queue, accumulated output, and the outbound WebSocket queue are also bounded. Overflow is fail-closed and reports `output_overflow` when the outbound queue still permits that error; output is never silently trimmed.

Output is flushed on newline, the 35ms bounded interval, the 512-byte threshold, or process exit. The interval is measured from the first byte in a pending batch; later bytes do not debounce or extend the deadline. UTF-8 fragments are retained across PTY chunks and invalid or incomplete bytes at finalization become deterministic replacement characters. A process exit waits for both the typed PTY-reader result and process Wait result, drains the chunk queue, flushes pending output, emits one exit event, drains the writer, closes the session, and reaps the child.

Client input is handled by a fixed-capacity queue and dedicated PTY writer. Text and interrupt controls retain arrival order; an interrupt is written as PTY byte `0x03` after earlier queued text. Queue overflow returns `input_overflow` when possible and closes the session fail-closed. PTY write blocking cannot prevent session cancellation because PTY close unblocks the writer.

Origin-less native clients are allowed. A browser Origin is accepted only when its host matches the request host. The server binds loopback by default; non-loopback binding requires `-allow-remote` and an external network safety boundary.
