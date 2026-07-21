<!-- Canonical public Project Story. Keep claims aligned with docs/submission/CLAIM_EVIDENCE_MATRIX.md. -->

# BOOTMUX — The Physical First Mile for Codex

> **Built by Codex. Architected and hardened with GPT-5.6. Proven through human-operated hardware.**

## Inspiration

AI is available during almost every part of my work—except the moment I need it most.

When I start setting up a new computer, recover a broken environment, or work on a machine that is not yet ready for remote development, the normal path to AI disappears. Codex is not installed. SSH may not be configured. The network path may not exist. Even copying a command can be impossible.

My workaround was painfully physical: wipe a dirty display, find a camera angle that makes the terminal readable, photograph an error, send it to ChatGPT, and then manually type the suggested command back into the machine.

It felt like being stranded on the median of a highway while everyone said, “Just cross it.” The missing piece was not another AI application. It was a way for AI to reach a computer **before that computer was ready for AI**.

That became BOOTMUX.

## What BOOTMUX does

**BOOTMUX creates the physical first mile for Codex.**

It combines an iPhone, an ESP32-S3, native USB HID, a target-side terminal Companion, and Codex into two deliberately separate paths.

### Physical input path

```text
iPhone
→ Bluetooth Low Energy
→ ESP32-S3
→ native USB HID keyboard
→ target computer
```

### Independently observed return path

```text
target PTY / Codex
→ BOOTMUX Companion
→ local WebSocket
→ iPhone terminal
```

The separation matters. Sending keyboard input does not prove that the target computer processed it, and an acknowledgement from the ESP32-S3 is not the same as observed terminal output. BOOTMUX only presents output that the target-side PTY actually returned.

In the demonstrated Build Week slice, bounded ASCII input was observed crossing the physical BLE-to-ESP32-S3-to-USB-HID path. A real target-side Codex prompt then returned the exact marker `BOOTMUX_READY` to the iPhone through the independently observed terminal path.

BOOTMUX is not simply an SSH client. SSH assumes the computer is already reachable and configured. BOOTMUX is designed for the earlier moment when that software path does not exist yet.

## How it works

BOOTMUX is intentionally asymmetric so the smallest credible end-to-end path could be completed and tested during Build Week.

| Layer | Technology | Responsibility |
| --- | --- | --- |
| iPhone client | Swift, SwiftUI, CoreBluetooth | Sends committed text over BLE and displays bounded, selectable terminal output |
| Physical bridge | ESP32-S3, BLE, USB HID | Converts bounded BLE frames into native USB keyboard input |
| Target Companion | Go, PTY, WebSocket | Owns terminal sessions and returns independently observed output |
| Codex path | Official Codex CLI, bounded adapter | Runs the target-side Codex prompt used in the end-to-end proof |
| Clean test environment | ARM64 Lima VM | Recreates the target environment and verifies installation and bootstrap behavior |
| Judge Mode | HTML, JavaScript, packaged Companion | Lets judges inspect the terminal experience without rebuilding the hardware stack |

The Go Companion includes session isolation, bounded input and output queues, output batching, UTF-8 handling, explicit overflow behavior, process cleanup, and fail-closed lifecycle rules.

The native iPhone client uses SwiftUI, CoreBluetooth, Foundation, `URLSessionWebSocketTask`, a selectable `UITextView` bridge, bounded terminal history, and streaming ANSI sanitization. It has no third-party iPhone runtime package dependency.

The ESP32-S3 firmware uses bounded owned frames, acknowledgements, duplicate handling, and explicit overflow behavior before presenting input as a native USB HID keyboard.

## How Codex and GPT-5.6 built BOOTMUX

BOOTMUX was **not** generated in one prompt. It was built through a repeated convergence loop with a declared END condition:

```text
Human product goal and END condition
↓
GPT-5.6 decomposition, contracts, risk analysis, and scope control
↓
Codex repository implementation, execution, tests, and evidence return
↓
GPT-5.6 review of code, failures, runtime output, and proof boundaries
↓
Bounded FIX instructions returned to Codex
↓
Codex repair and re-validation
↓
Human physical acceptance—or an explicit unresolved gate
```

Codex served as the implementation and execution engine. It implemented and repaired the Go Companion, native SwiftUI client, ESP32-S3 firmware, ARM64 VM harness, Codex adapter, Judge Mode, tests, and validation tooling.

GPT-5.6 served as the architecture, adversarial review, and convergence layer. It converted the product idea into bounded implementation contracts, separated physical input from independently observed output, constrained scope, reviewed lifecycle and overflow behavior, identified ownership and path-binding failures, and protected the boundary between code-green and physically proven claims.

Human judgment remained responsible for the product direction, hardware selection, END condition, physical setup, real-device observations, acceptance or rejection of repairs, and every final public claim.

This loop compressed a multi-domain development effort—Go, SwiftUI, CoreBluetooth, BLE, ESP32-S3 firmware, USB HID, PTY/WebSocket behavior, ARM64 virtualization, Codex CLI integration, evidence, Judge Mode, and video preparation—into the Build Week period without treating unverified work as complete.

## Challenges I ran into

### 1. Sent input is not observed output

The first architectural danger was accidentally treating “the bridge accepted my text” as proof that the target or Codex had processed it.

The solution was the asymmetric architecture: physical input travels through BLE and USB HID, while results return from a target-side PTY through a separate Companion. This makes the evidence boundary visible instead of hiding it behind a successful-looking UI.

### 2. BLE queue ownership caused physical instability

An early firmware path placed non-trivial `String` objects inside a raw-copy FreeRTOS queue. It looked plausible in code, but ownership semantics made the physical transport unstable.

GPT-5.6 identified the root ownership hazard. Codex replaced the queued objects with bounded POD-owned frames and explicit overflow handling. The repaired short-operation path then completed the observed transport sequence without the previous disconnect.

### 3. Cross-process paths could silently disagree

During the HID Mirror work, GPT-5.6 found that the physical launcher and the target process could resolve different transcript paths. It also found that replacing a file while a writer remained open could leave a stale writer attached to the old inode.

Codex unified the VM-relative path and changed transcript bounding to fail closed rather than silently trimming underneath an open writer.

### 4. The final 20 percent is harder than the first demo

The most common failure in AI-assisted development is not a lack of generated code. It is stopping after a convincing first demo while lifecycle bugs, physical acceptance, packaging, evidence, privacy review, video, and submission remain unfinished.

BOOTMUX addressed that by declaring the END condition first, giving Codex bounded tasks, requiring concrete evidence, rejecting false completion, freezing nonessential features near submission, and treating Judge Mode, documentation, and the demo video as product gates rather than optional polish.

## Accomplishments I’m proud of

- One human builder coordinated hardware, firmware, native iOS, systems programming, virtualization, Codex integration, testing, evidence, and submission work during Build Week.
- Codex implemented the major product layers and repeatedly repaired them after independent review.
- GPT-5.6 reviews changed real implementation behavior rather than only generating prose or ideas.
- A bounded physical ASCII path was observed from the iPhone through BLE and ESP32-S3 USB HID to the target.
- A real Codex result, `BOOTMUX_READY`, was observed returning from the target to the iPhone.
- The official Codex CLI installation and bounded probes passed in a clean ARM64 Lima VM.
- A no-rebuild Judge Mode gives reviewers a practical way to inspect the terminal-and-copy experience without owning the hardware.
- Unproven capabilities remained explicit gates instead of becoming marketing claims.

## What I learned

The hardest part of AI-assisted development is not generating the first 80 percent. It is keeping fast agents aligned long enough to close lifecycle bugs, physical acceptance, evidence, packaging, video, and delivery.

The most effective pattern was:

1. declare a measurable END condition before implementation;
2. convert the goal into bounded contracts;
3. let Codex implement, execute, and return evidence;
4. let GPT-5.6 independently review both the code and the proof;
5. return narrow root-cause repairs to Codex;
6. keep human authority over physical acceptance and final claims.

Codex supplied implementation velocity. GPT-5.6 supplied architectural and verification pressure. Human judgment kept the loop aimed at a real, demonstrable END state.

## Try it and judge instructions

The full source and setup documentation are available in the [BOOTMUX GitHub repository](https://github.com/oxcandy-lgtm/BOOTMUX/tree/agent/bootstrap-design-roadmap).

Judges can inspect the terminal experience without rebuilding the project:

- Open [`judge/index.html`](https://github.com/oxcandy-lgtm/BOOTMUX/blob/agent/bootstrap-design-roadmap/judge/index.html) for the standalone offline replay.
- Follow the [Judge Mode instructions](https://github.com/oxcandy-lgtm/BOOTMUX/blob/agent/bootstrap-design-roadmap/judge/README.md) for the packaged macOS arm64 or live local Companion path.

Judge Mode demonstrates the terminal, session, selection, and copy experience. It is clearly labeled and is **not** presented as proof of the physical BLE or USB HID path.

### Supported platforms

- iPhone client: iOS 17 or later
- Packaged Judge Mode: macOS arm64
- Standalone Judge Replay: modern browser, no build required
- Companion development path: verified in the declared Unix-like environment and a clean ARM64 Lima VM
- Physical bridge: ESP32-S3 with BLE and native USB HID keyboard support

## Current evidence boundary

### Demonstrated or observed in the current Build Week slice

- Go Companion and PTY/WebSocket terminal core
- native SwiftUI iPhone client implementation
- bounded BLE transport and native USB HID ASCII delivery
- clean ARM64 VM Codex installation and bounded probes
- physical Codex `BOOTMUX_READY` return to the iPhone
- standalone and packaged Judge Mode

### Not claimed as complete

- repeatable production-ready physical operation
- Unicode HID or mouse support
- full terminal emulation
- completely offline target operation
- continued post-bootstrap operation
- physical selectable-copy, CLEAR, or HID Mirror acceptance until owner-confirmed

## What’s next

The immediate next step is to make the demonstrated first-mile path repeatable and easier to provision while preserving the distinction between sent input and independently observed output.

Near-term work includes physical copy and CLEAR acceptance, HID Mirror acceptance, repeatability receipts, simpler packaging, and broader platform testing. Later versions may add Unicode HID, mouse input, recovery capsules, and guided provisioning workflows.

The long-term goal is simple:

> **When a computer is not ready for AI, BOOTMUX creates the first path that lets AI help make it ready.**
