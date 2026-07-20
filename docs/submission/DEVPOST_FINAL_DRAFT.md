# BOOTMUX Devpost Final Draft

Status: working public-safe draft. A human must perform the final wording, registration, category, video, and submission review.

## Project title

BOOTMUX — The Physical First Mile for Codex

## Short description

Codex built BOOTMUX, a physical first mile for Codex: iPhone text crosses BLE and ESP32-S3 USB HID, while independently observed terminal output returns to the phone—architected with GPT-5.6.

## Inspiration / Story

AI is present in my daily life almost all the time. Yet the moment I begin setting up a server PC, the normal way to communicate with that AI disappears. I end up wiping a dirty display, adjusting the focus, and searching for the one camera angle that makes a terminal readable before sending a photograph to ChatGPT.

It feels like being dropped on the median strip in the middle of a highway. Other drivers stare as they pass. People say, “Just cross the highway and keep going,” as if that were easy. But I am a baby when it comes to terminal work. If merely typing into the terminal is already a miracle, can you really expect me to crawl across the highway on all fours?

That is the gap BOOTMUX is built to close. Before SSH, remote tooling, or a normal AI workflow is ready, BOOTMUX creates a physical first mile: an iPhone can send committed text through BLE and an ESP32-S3 USB HID keyboard path, while independently observed target and Codex output returns through a small Companion to the phone.

## Category

Developer Tools.

## What it does

BOOTMUX combines a native SwiftUI iPhone client, an ESP32-S3 BLE-to-USB-HID bridge, a Go PTY Companion, a versioned WebSocket protocol, an ARM64 VM harness, and a bounded Codex adapter.

The demonstrated input path is:

```text
iPhone → BLE → ESP32-S3 → USB HID → target
```

The independently observed return path is:

```text
target PTY / Codex → Companion → local WebSocket → iPhone
```

The owner has observed bounded physical ASCII input and a real Codex `BOOTMUX_READY` result returning to the iPhone. A standalone replay and packaged live Judge Mode let judges inspect the terminal-and-copy experience without rebuilding the hardware stack. Judge Mode is clearly labeled and is not presented as physical HID proof.

## How it was built

The Companion is a small Go executable with PTY integration, session isolation, bounded queues, output batching, UTF-8 handling, and fail-closed lifecycle behavior. The native iPhone client uses SwiftUI, CoreBluetooth, Foundation, `URLSessionWebSocketTask`, a `UITextView` selection bridge, bounded terminal history, and a streaming ANSI sanitizer. The ESP32-S3 firmware owns bounded BLE frames and presents native USB HID keyboard input to the target. The VM tooling creates a clean ARM64 environment, installs the official Codex CLI, provisions the Companion, and runs a bounded one-shot Codex prompt.

There are no external iPhone runtime packages.

## How Codex and GPT-5.6 were used

BOOTMUX was not generated in one prompt. It was developed through a repeated convergence loop:

```text
human goal and END condition
→ GPT-5.6 decomposition, contracts, and risk review
→ Codex repository implementation, execution, and tests
→ GPT-5.6 review of code, failures, and evidence
→ bounded FIX instructions returned to Codex
→ Codex repair and re-validation
→ human physical acceptance
```

Codex implemented and repaired the Go Companion, SwiftUI client, ESP32-S3 firmware, ARM64 VM harness, Codex adapter, Judge Mode, and tests. GPT-5.6 designed the asymmetric physical-input / independently-observed-output architecture, converted product intent into bounded implementation contracts, reviewed lifecycle and overflow behavior, identified the BLE queue ownership hazard, audited the HID Mirror path binding, and protected the boundary between code-green and physically proven claims.

The loop continued beyond the first working demo into evidence tracking, privacy boundaries, Judge Mode, narrated video planning, and submission closeout. Codex supplied implementation velocity; GPT-5.6 supplied architectural and verification pressure; human judgment kept the work aimed at a real, demonstrable END state.

Concrete mappings are in [CODEX_GPT56_EVIDENCE_LEDGER.md](CODEX_GPT56_EVIDENCE_LEDGER.md) and [CODEX_GPT56_DEVELOPMENT_LOOP.md](CODEX_GPT56_DEVELOPMENT_LOOP.md).

## Challenges and accomplishments

The central challenge was preserving the distinction between text sent by a client and output actually observed from the target. Acknowledging HID input is not the same as proving terminal or Codex output.

The development loop found failures that a happy-path demo would have hidden. GPT-5.6 reviews led Codex through Companion lifecycle repairs, replacement of unsafe non-trivial objects in the FreeRTOS queue with bounded POD-owned frames, and correction of mismatched VM transcript paths and stale-writer risk in the HID Mirror path.

Within the Build Week period, one human builder coordinated Go, SwiftUI, CoreBluetooth, ESP32-S3 firmware, USB HID, PTY/WebSocket behavior, an ARM64 VM, the official Codex CLI, Judge Mode, evidence, and video preparation. No exact hour-count claim is made; the defensible result is rapid multi-domain convergence without declaring unverified work complete.

## What was learned

The hard problem in AI-assisted development is not producing the first 80 percent. It is keeping multiple fast agents aligned long enough to close lifecycle bugs, physical acceptance, evidence, packaging, and submission.

The most effective pattern was to declare an END condition first, give Codex bounded implementation tasks, require concrete evidence, let GPT-5.6 independently review both code and proof, and keep human authority over physical acceptance and final claims.

## What's next

Selectable physical copy, visible CLEAR feedback, physical HID Mirror acceptance, and repeatability remain evidence gates. Unicode HID, mouse support, background operation, full terminal emulation, production readiness, and cloud services are deferred.

The next product step is to turn the demonstrated first-mile path into a repeatable recovery and provisioning tool without weakening the current distinction between sent input and independently observed output.

## Judge instructions

Open [`judge/index.html`](../../judge/index.html) directly for offline replay, or use the packaged macOS arm64 Judge Mode in `dist/bootmux-judge-macos-arm64/`. For live mode, start the Companion on loopback and open `/judge`. The Judge Mode disclaimer must remain visible.

## Supported platforms

The Companion is locally verified on the declared Unix-like development target and in a clean ARM64 Lima VM. The iPhone app targets iOS 17 or later; its launch canvas, bounded physical ASCII path, and physical `BOOTMUX_READY` return are owner-observed. The packaged Judge Mode is macOS arm64; the standalone HTML replay is platform-independent.

## Submission fields still requiring human action

```yaml
video_url: PLACEHOLDER_PENDING_PUBLIC_YOUTUBE_UPLOAD
feedback_session_id: PRIVATE_NOT_STORED_IN_REPOSITORY
registration: HUMAN_CONFIRMATION_PENDING
final_claim_review: HUMAN_CONFIRMATION_PENDING
```
