# BOOTMUX Devpost Final Draft

Status: working public-safe draft. A human must perform the final wording, registration, category, video, and submission review.

## Project title

BOOTMUX — A Terminal Path into an Unready Computer

## Short description

Conceived and architected with GPT-5.6, BOOTMUX gives an iPhone a selectable terminal path into a target PC, backed by a Codex-built Companion and a no-rebuild Judge Mode.

## Inspiration / Story

AI is present in my daily life almost all the time. Yet the moment I begin setting up a server PC, the normal way to communicate with that AI disappears. I end up wiping a dirty display, adjusting the focus, and searching for the one camera angle that makes a terminal readable before sending a photograph to ChatGPT.

It feels like being dropped on the median strip in the middle of a highway. Other drivers stare as they pass. People say, “Just cross the highway and keep going,” as if that were easy. But I am a baby when it comes to terminal work. If merely typing into the terminal is already a miracle, can you really expect me to crawl across the highway on all fours?

That is the gap BOOTMUX is built to close. Either operating systems will have native AI available from the beginning, or we need a bootstrap path that lets an ordinary person reach AI before the target computer is ready. BOOTMUX is an attempt to build that path: a target-side Companion, a selectable terminal surface, and a future bridge from the physical phone to the computer.

This is an owner voice working draft. Before final submission, the owner will revise the English while preserving the humor, the “baby” metaphor, and the distinction between the working software path and future hardware claims.

## Category

Developer Tools.

## What it does

The current submission slice contains a target-side PTY Companion, a versioned WebSocket protocol, a native SwiftUI iPhone terminal client implementation, bounded observed output, and a standalone/live Judge Mode. The terminal view is selectable and supports native copy behavior. Judge Mode can replay `BOOTMUX_READY` offline or connect to the local Companion and show observed PTY output.

## How it was built

The Companion is a small Go executable with production PTY integration, session isolation, bounded queues, output batching, UTF-8 handling, and fail-closed lifecycle behavior. The iPhone client uses SwiftUI, Foundation, `URLSessionWebSocketTask`, a `UITextView` selection bridge, bounded terminal history, and a streaming ANSI sanitizer. There are no external iPhone runtime packages.

## How Codex and GPT-5.6 were used

Codex was used for the V0A Companion, V0B iPhone client, lifecycle repairs, Judge Mode, and submission evidence. GPT-5.6 contributed to the asymmetric transport architecture, protocol contracts, bounded output and UI behavior, edge-case repairs, claim safety, and submission structure. Concrete mappings are in [CODEX_GPT56_EVIDENCE_LEDGER.md](CODEX_GPT56_EVIDENCE_LEDGER.md).

## Challenges and accomplishments

The central challenge was preserving the distinction between text sent by a client and output actually observed from a PTY. The project now has a bounded local terminal path, an owner-observed physical ASCII keyboard path with a `BOOTMUX_READY` return, and a judge-accessible replay/live mode. Copy confirmation, CLEAR feedback, repeatability, and continued post-bootstrap use remain honest gates.

## What was learned

The smallest credible product slice is a target-side Companion plus a selectable terminal surface. Hardware transport, claim evidence, and submission evidence must be tracked separately so a working software path is useful without being mistaken for physical proof.

## What's next

The owner has observed the bounded physical BLE-to-ESP32-S3/native USB HID ASCII path and a physical Codex `BOOTMUX_READY` return. Selectable copy, visible CLEAR feedback, repeatability, and continued post-bootstrap use remain evidence gates. Unicode HID, mouse support, background operation, full terminal emulation, production readiness, and cloud services are deferred.

## Judge instructions

Open [`judge/index.html`](../../judge/index.html) directly for offline replay, or use the packaged macOS arm64 Judge Mode in `dist/bootmux-judge-macos-arm64/`. For live mode, start the Companion on loopback and open `/judge`. The Judge Mode disclaimer must remain visible.

## Supported platforms

The Companion is locally verified on the declared Unix-like development target and in a clean ARM64 Lima VM. The iPhone app targets iOS 17 or later; its launch canvas, bounded physical ASCII path, and physical `BOOTMUX_READY` return are owner-observed. The packaged Judge Mode is macOS arm64; the standalone HTML replay is platform-independent. This remains a working draft for owner revision before submission.

## Submission fields still requiring human action

```yaml
video_url: PLACEHOLDER_PENDING_PUBLIC_YOUTUBE_UPLOAD
feedback_session_id: PRIVATE_NOT_STORED_IN_REPOSITORY
registration: HUMAN_CONFIRMATION_PENDING
final_claim_review: HUMAN_CONFIRMATION_PENDING
```
