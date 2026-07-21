# Codex + GPT-5.6 Development Loop

## Why this matters

BOOTMUX was not produced by a single prompt or a one-pass code generation session. It was completed through a repeated convergence loop that used each participant for a distinct role:

```text
Human product intent and END condition
↓
GPT-5.6 decomposition, contracts, risk analysis, and scope control
↓
Codex repository implementation, execution, testing, and evidence return
↓
GPT-5.6 adversarial review of code, runtime output, and proof boundaries
↓
Bounded FIX instructions returned to Codex
↓
Codex repair and re-validation
↓
Human physical acceptance or explicit rejection
↓
Repeat until the declared END condition or an honest remaining gate
```

The goal of the loop was not to maximize generated code. Its goal was to minimize the distance between an ambiguous human idea and a working, evidenced, submit-ready product.

## Role separation

### Human

- identified the dirty-display and unready-computer problem;
- selected the iPhone and ESP32-S3 hardware direction;
- declared the Hackathon V1 END condition;
- connected and operated the real devices;
- accepted or rejected proposed repairs;
- recorded physical evidence;
- owns the final video, claims, and submission.

### GPT-5.6

- converted product intent into bounded implementation contracts;
- separated physical input from independently observed target output;
- constrained scope when implementation threatened to expand;
- reviewed code, test results, runtime evidence, and claim boundaries;
- identified hidden lifecycle, ownership, stale-state, and path-binding failures;
- converted failures into narrow Codex-ready repair instructions;
- preserved the distinction between code-green, VM-observed, owner-observed, and unproven states.

### Codex

- read and modified the repository;
- implemented the Go Companion and PTY/WebSocket protocol;
- implemented the native SwiftUI client and tests;
- implemented and repaired the ESP32-S3 BLE-to-USB-HID firmware;
- built the ARM64 VM, official Codex installation, forwarder, and adapter path;
- executed tests, builds, probes, and repair cycles;
- returned concrete outputs and repository evidence for review.

## Convergence controls

The loop used explicit controls to prevent the common failure mode where an AI-built project stops at approximately 80 percent completion:

1. **Declare the END condition first.** For V1, the marker was a real Codex `BOOTMUX_READY` result reaching the iPhone through the demonstrated path.
2. **Use bounded tasks.** Each Codex dispatch had a narrow scope, stop rules, forbidden overclaims, and required evidence.
3. **Separate implementation from proof.** Unit tests, VM observations, physical observations, and edited demo footage were never treated as interchangeable.
4. **Reject false completion.** A code-green feature remained pending when physical acceptance was missing.
5. **Repair root causes, not screenshots.** Failures were converted into specific contract repairs before another run.
6. **Freeze features near submission.** New work was allowed only when it closed a demonstrated V1 or Build Week blocker.
7. **Treat the video and submission as product gates.** The loop continued past implementation into Judge Mode, licensing, README evidence, privacy review, narration, and final submission preparation.

## Concrete loop evidence

### Companion lifecycle loop

Codex implemented the target-side Companion. GPT-5.6 then reviewed timer flush behavior, PTY reader synchronization, process reaping, outbound close ownership, slow-client overflow, UTF-8 boundaries, interrupts, and descendant cleanup. Codex repaired these contracts across V0A R1–R3 and reran unit, race, stress, build, and live probes.

### BLE ownership loop

The initial physical transport path exposed instability. GPT-5.6 identified that non-trivial `String` objects were being placed in a raw-copy FreeRTOS queue. Codex replaced them with bounded POD-owned frames and explicit overflow handling. The subsequent observed short run completed `OPENED` plus eight `APPLIED` acknowledgements without the previous transport disconnect.

### Physical demo and Mirror loop

Codex implemented endpoint persistence, COPY ALL, CLEAR, FOLLOW, a physical launcher, and a read-only HID Mirror. GPT-5.6 reviewed the resulting paths and found that the launcher and HID target could resolve different transcript locations, while replace-under-open-writer trimming could leave a stale writer. Codex unified the VM-relative path and changed transcript bounding to explicit fail-closed behavior.

These examples demonstrate the full loop:

```text
implementation
→ evidence
→ independent review
→ bounded repair
→ re-validation
```

## Rapid development claim

BOOTMUX may state that this loop enabled one human builder to coordinate multiple technical domains within the short Build Week period:

```text
Go + PTY + WebSocket
SwiftUI + CoreBluetooth
ESP32-S3 + BLE + USB HID
ARM64 VM + Codex CLI
Judge Mode + evidence + narrated submission
```

It must not claim an exact hour count unless independently documented. The defensible claim is that repeated Codex implementation and GPT-5.6 review compressed a multi-domain development process into the Build Week submission period while retaining human physical acceptance and explicit unresolved gates.

## Video-ready explanation

> BOOTMUX was not generated in one prompt. I set the product goal and physical direction. GPT-5.6 repeatedly converted that intent into bounded contracts and reviewed the resulting code and evidence. Codex implemented those contracts across Go, SwiftUI, ESP32-S3 firmware, and an ARM64 VM, then reran the repairs. This loop continued beyond the first working demo into testing, Judge Mode, evidence, and the final submission.

## Central claim

> **Codex supplied implementation velocity. GPT-5.6 supplied architectural and verification pressure. Human judgment kept the loop aimed at a real, demonstrable END state.**

This document describes a public-safe development process. It does not publish the Primary Codex Thread, its Session ID, private prompts, credentials, device identifiers, or private infrastructure details.
