# BOOTMUX Devpost Final Draft

Status: working public-safe draft. A human must perform the final wording, registration, category, video, and submission review.

## Project title

BOOTMUX — A Terminal Path into an Unready Computer

## Short description

BOOTMUX gives an iPhone a selectable terminal path into a target computer through a local Companion, with a no-rebuild Judge Mode for the terminal-and-copy experience.

## Category

Developer Tools.

## What it does

The current submission slice contains a target-side PTY Companion, a versioned WebSocket protocol, a native SwiftUI iPhone terminal client implementation, bounded observed output, and a standalone/live Judge Mode. The terminal view is selectable and supports native copy behavior. Judge Mode can replay `BOOTMUX_READY` offline or connect to the local Companion and show observed PTY output.

## How it was built

The Companion is a small Go executable with production PTY integration, session isolation, bounded queues, output batching, UTF-8 handling, and fail-closed lifecycle behavior. The iPhone client uses SwiftUI, Foundation, `URLSessionWebSocketTask`, a `UITextView` selection bridge, bounded terminal history, and a streaming ANSI sanitizer. There are no external iPhone runtime packages.

## How Codex and GPT-5.6 were used

Codex was used for the V0A Companion, V0B iPhone client, lifecycle repairs, Judge Mode, and submission evidence. GPT-5.6 contributed to the asymmetric transport architecture, protocol contracts, bounded output and UI behavior, edge-case repairs, claim safety, and submission structure. Concrete mappings are in [CODEX_GPT56_EVIDENCE_LEDGER.md](CODEX_GPT56_EVIDENCE_LEDGER.md).

## Challenges and accomplishments

The central challenge was preserving the distinction between text sent by a client and output actually observed from a PTY. The project now has a bounded local terminal path and a judge-accessible replay/live mode while retaining honest boundaries around unfinished hardware and bootstrap paths.

## What was learned

The smallest credible product slice is a target-side Companion plus a selectable terminal surface. Hardware transport, claim evidence, and submission evidence must be tracked separately so a working software path is useful without being mistaken for physical proof.

## What's next

Physical iPhone acceptance, BLE-to-ESP32-S3 input, native USB HID enumeration, and a Codex `BOOTMUX_READY` run remain future evidence gates. Mouse support, background operation, full terminal emulation, and cloud services are deferred.

## Judge instructions

Open [`judge/index.html`](../../judge/index.html) directly for offline replay, or use the packaged macOS arm64 Judge Mode in `dist/bootmux-judge-macos-arm64/`. For live mode, start the Companion on loopback and open `/judge`. The Judge Mode disclaimer must remain visible.

## Supported platforms

The Companion is locally verified on the declared Unix-like development target. The iPhone app targets iOS 17 or later but awaits Xcode and physical-device validation. The packaged Judge Mode is macOS arm64; the standalone HTML replay is platform-independent.

## Submission fields still requiring human action

```yaml
video_url: PLACEHOLDER_PENDING_PUBLIC_YOUTUBE_UPLOAD
feedback_session_id: PRIVATE_NOT_STORED_IN_REPOSITORY
registration: HUMAN_CONFIRMATION_PENDING
final_claim_review: HUMAN_CONFIRMATION_PENDING
```
