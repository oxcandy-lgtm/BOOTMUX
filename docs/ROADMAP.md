# BOOTMUX Roadmap

## Roadmap policy

The roadmap is gate-driven rather than date-driven. A phase is complete only when its acceptance evidence exists. Stretch features must not destabilize the core demonstration.

This file is the core product roadmap. The independent [SAI Research Roadmap](SAI_RESEARCH_ROADMAP.md) defines the H0–H8 evidence gates for EPOCHROOT, TTYRETINA, SYNDROMUX, SYNDCOMP, VOIDCODE, CAUSALCLOCK, STRATAROOT, ROOTFIT, and effect-bounded experiments. Research features may enter this core path only after they have deterministic fallbacks and measured evidence.

Priority order:

```text
physical input
→ reliable transport
→ verified terminal
→ safe diagnosis
→ proof-carrying recovery
→ target-side Codex handoff
```

## R0 — Public repository and contracts

### Goal

Establish a safe public specification before implementation begins.

### Deliverables

- project overview;
- architecture blueprint;
- core roadmap;
- SAI research hypotheses and evidence roadmap;
- security policy;
- publication-safety rules;
- secret-safe ignore rules;
- terminology and scope boundaries.

### Acceptance gate

- no personal contact details;
- no credentials or tokens;
- no private hostnames, addresses, local paths, or production logs;
- all examples are synthetic;
- destructive operations are explicitly out of scope for automatic execution;
- research hypotheses are identified as unvalidated until reproducible evidence exists;
- SAI-originated synthesis is attributed without claiming invention of established foundations.

## R1 — Transport and HID proof

### Goal

Prove that the iPhone can control the target through ESP32-S3 without target-side software.

### Deliverables

- BLE GATT connection between iPhone and ESP32-S3;
- USB HID mouse;
- USB HID keyboard;
- active-output state machine;
- sequence numbers and duplicate suppression;
- emergency stop;
- disconnect-safe neutral input state.

### Acceptance gate

- pointer movement and click work repeatedly;
- keyboard input works for a documented baseline layout;
- reconnect does not replay stale input;
- no duplicated events after transport retry;
- emergency stop prevents further output;
- no device identifier is written to public logs.

## R2 — iPhone interaction surfaces

### Goal

Deliver the three-tab operator experience.

### Deliverables

- PAD tab;
- TERMINAL tab with synthetic Stage 0 status;
- AI tab;
- collapsible system keyboard;
- connection and route indicators;
- native text selection and copy behavior;
- approval, rejection, and stop controls.

### Acceptance gate

- all three tabs work on a physical iPhone;
- PAD gestures map deterministically to HID events;
- committed text is preserved within the supported Stage 0 constraints;
- terminal status clearly distinguishes sent input from verified output;
- stop remains reachable from every primary surface.

## R3 — USB data channel and Companion

### Goal

Upgrade from one-way HID input to a verified live terminal.

### Deliverables

- USB data interface;
- framed protocol;
- Companion process;
- PTY management;
- stdout, stderr, and exit-status events;
- bounded buffering and backpressure;
- exact Unicode insertion after Companion starts;
- local session persistence;
- measurement hooks required by SAI research phase H0.

### Acceptance gate

- Companion starts through the documented bootstrap path;
- terminal output is displayed without being mislabeled;
- process exit status reaches the iPhone;
- Unicode text round-trips correctly in the supported environment;
- reconnect resumes or fails closed without mixing sessions;
- logs are bounded and redacted before leaving the target;
- the transport can report bytes, frames, retransmissions, and reconnect cost without exposing private data.

## R4 — Terminal skills and capsules

### Goal

Convert raw terminal failures into compact, useful machine context.

### Deliverables

- deterministic event detector;
- initial Terminal Skill taxonomy;
- repeated-failure and stall detection;
- Context Capsule schema;
- secret and personal-data redaction;
- compact ESP32-S3 recovery record;
- user-readable session timeline;
- deterministic fallback path for any experimental TTYRETINA integration.

### Acceptance gate

- a controlled permission failure is classified correctly;
- a command-not-found failure is classified correctly;
- an unknown failure remains explicitly unknown;
- secret-like fixture values are removed from outbound capsules;
- raw full logs are not transmitted by default;
- restart resumes from the last verified stage;
- semantic terminal processing cannot discard the bounded raw evidence required for fallback.

## R5 — Policy gate and proof-carrying recovery

### Goal

Use GPT-5.6 for reasoning while keeping execution deterministic and reviewable.

### Deliverables

- Recovery Capsule schema;
- risk and approval classes;
- structured tool registry;
- executable-and-argument executor;
- evidence collector and verifier;
- approval UI;
- rollback boundary metadata;
- model-output validation;
- explicit abstention state for insufficient or contradictory evidence;
- extension points for Policy-Certified Probe Prefix, SYNDCOMP, SYNDROMUX, and VOIDCODE experiments.

### Acceptance gate

- read-only probes can run through the policy gate;
- mutation cannot run without required approval;
- denied actions remain blocked even when requested by model output;
- no model-generated string is passed directly to a shell interpreter;
- a controlled repair produces a matching Evidence Receipt;
- the model cannot independently mark its proposal successful;
- an unknown or underdetermined incident cannot be forced into an automatic mutation path;
- experimental diagnostic compilation can be disabled without disabling the core deterministic recovery path.

## R6 — Target-side Codex bootstrap

### Goal

Install and activate Codex on the target, then transfer control from phone-side reasoning.

### Deliverables

- prerequisite inspection;
- user-controlled authentication flow;
- installation Recovery Capsule;
- installation evidence;
- Codex event bridge;
- Handoff Capsule;
- runtime selector transition to `CODEX`;
- versioned evidence dependencies suitable for future CAUSALCLOCK and STRATAROOT experiments.

### Acceptance gate

- Codex is absent at the beginning of the test;
- installation requires visible approval;
- authentication secrets are never exposed to the model or logs;
- executable path and version are verified;
- a simple target-side Codex task runs;
- the iPhone UI displays the runtime transition and resulting events;
- success evidence remains distinguishable from counterfactual or simulated results.

## R7 — Integrated demonstration

### Goal

Demonstrate the full BOOTMUX thesis on one supported target platform.

### Required demo sequence

1. connect ESP32-S3 to the target;
2. connect iPhone to ESP32-S3;
3. control pointer and keyboard;
4. start Companion through the bootstrap path;
5. display verified live terminal output;
6. trigger a controlled failure;
7. classify the failure automatically;
8. generate a GPT-5.6 Recovery Capsule;
9. approve and execute a bounded repair;
10. verify the state transition from target evidence;
11. install and activate Codex;
12. hand off to target-side Codex;
13. complete one repository-scale task;
14. stop or disconnect safely.

### Acceptance gate

- the demo can be repeated from a documented clean state;
- every stage reports explicit success or failure;
- no manual hidden terminal is used to bypass the demonstrated path;
- no credentials or personal information appear in the recording;
- failure paths remain honest and recoverable;
- the core demo remains reproducible with every SAI research optimization disabled;
- enabled research components report raw measurements and do not present targets as achieved results.

## SAI research overlay

The SAI research program is deliberately separated from the primary R0–R7 completion claim.

```text
H0 measurement and replay
→ H1 TTYRETINA
→ H2 EPOCHROOT
→ H3 SYNDCOMP and SYNDROMUX
→ H4 VOIDCODE
→ H5 CAUSALCLOCK and STRATAROOT
→ H6 ROOTFIT
→ H7 Effect-Bounded Experiment Cell
→ H8 integrated sparse recovery experiment
```

Promotion into the core implementation requires:

- deterministic fallback behavior;
- versioned public schemas;
- negative safety tests;
- a measured improvement or safety property;
- an explicit disable switch;
- honest support, revision, or rejection based on benchmark evidence.

See [SAI Research Roadmap](SAI_RESEARCH_ROADMAP.md) for full phase definitions and gates.

## Stretch tracks

These remain isolated until the integrated demo is stable.

### S1 — Additional target platform

Port Companion and bootstrap contracts to a second operating system.

### S2 — Wi-Fi and hotspot routes

Evaluate ESP32-S3 Wi-Fi, target hotspot connectivity, and route selection.

### S3 — Application-specific phone relay

Research whether selected target-agent traffic can be relayed through the iPhone without presenting it as general-purpose tethering.

### S4 — GPIO and serial management

Add power, reset, boot-mode, and UART capabilities using hardware-specific adapters and strong safety controls.

### S5 — Local phone model

Add an optional phone-local classifier or summarizer for offline diagnosis. It must not bypass the policy gate.

### S6 — Signed updates and device identity

Introduce signed firmware, Companion release verification, and privacy-preserving device enrollment.

## Suggested repository layout

```text
BOOTMUX/
├── README.md
├── SECURITY.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── SAI_RESEARCH_HYPOTHESES.md
│   ├── SAI_RESEARCH_ROADMAP.md
│   └── PUBLICATION_SAFETY.md
├── protocol/
│   ├── schemas/
│   └── fixtures/
├── firmware/
│   └── esp32-s3/
├── ios/
│   └── BootMuxApp/
├── companion/
│   ├── core/
│   └── platform/
├── policy/
│   ├── tools/
│   └── rules/
├── tests/
│   ├── protocol/
│   ├── redaction/
│   ├── policy/
│   └── integration/
└── demo/
    ├── scripts/
    └── evidence/
```

## Initial implementation rule

Do not start by building every component at once.

The first executable vertical slice should be:

```text
iPhone gesture
→ BLE message
→ ESP32-S3
→ USB HID event
→ target response visible to the user
```

The second vertical slice should be:

```text
target PTY output
→ Companion
→ USB data
→ ESP32-S3
→ BLE
→ selectable iPhone terminal
```

The first research vertical slice should be:

```text
synthetic PTY fixture
→ deterministic TTYRETINA event
→ fixed two-fault hypothesis matrix
→ three read-only probes
→ compact syndrome
→ Evidence Receipt
→ byte and round-trip comparison
```

Only after both core slices are reliable should cloud reasoning and Codex installation be added. Research automation must not be allowed to bypass those gates.
