# BOOTMUX Architecture Blueprint

> **Design archive — not current implementation status.**

This page is the safe entry point to the original long-form BOOTMUX architecture design. The complete original text is preserved byte-for-byte in [Architecture Blueprint — Original](ARCHITECTURE_BLUEPRINT_ORIGINAL.md).

The original blueprint intentionally describes the full product vision, including components that are not implemented in the current Build Week slice: mouse input, a USB data return channel, automated event classification, Context and Recovery Capsules, a deterministic policy gate, a structured executor, evidence-verifying recovery, and long-running agent handoff.

For the implemented architecture and exact current boundary, read:

- [BOOTMUX Architecture](ARCHITECTURE.md)
- [Claim and Evidence Matrix](submission/CLAIM_EVIDENCE_MATRIX.md)
- [Build Week Status](submission/BUILD_WEEK_STATUS.md)

## Current public boundary

Demonstrated or owner-observed:

- bounded physical printable-ASCII input through iPhone → BLE → ESP32-S3 → native USB HID;
- independently observed PTY and Codex output through the Go Companion and local WebSocket;
- official Codex CLI installation and bounded probes in a clean ARM64 Lima VM;
- a physical `BOOTMUX_READY` return to the iPhone;
- standalone, packaged, and live local Judge Mode.

Not claimed as complete:

- the full architecture illustrated by the original blueprint;
- repeatable production-ready operation;
- physical copy/CLEAR or HID Mirror acceptance;
- mouse or Unicode HID;
- autonomous policy-gated recovery;
- full terminal emulation or continued post-bootstrap operation.

The original document remains valuable as BOOTMUX's complete product and research direction, but its future-tense design statements must not be used as evidence of current implementation.