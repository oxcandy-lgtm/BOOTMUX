# BOOTMUX Roadmap

```yaml
roadmap_status:
  V0:
    status: IMPLEMENTED_AWAITING_PHYSICAL_IPHONE_PROOF
  V1:
    status: BLE_TRANSPORT_STABILITY_VERIFIED_AWAITING_FULL_PHYSICAL_ACCEPTANCE
    task: BOOTMUX-V1-R7-BLE-TRANSPORT-ROOT-FIX-AND-V1-CLOSEOUT
  V2:
    status: PARTIALLY_IMPLEMENTED
  V3:
    status: OPEN
  V4:
    status: PARTIAL_BOUNDED_LOCAL_CODEX_RUN_ONLY
```

Feature development is reopened only for the V1 physical keyboard gate. All other frozen scope remains unchanged.

## Roadmap policy

BOOTMUX currently has one implementation priority:

> Complete the smallest repeatable Hackathon V1 before building the full product or validating the SAI research program.

The roadmap is gate-driven. A phase is complete only when its acceptance evidence exists.

The current target is defined in [Hackathon V1](HACKATHON_V1.md).

```text
V0 software loop
→ V1 physical keyboard path
→ V2 terminal return
→ V3 Codex installation
→ V4 Codex connectivity and copy
→ repeatable final demonstration
```

Research phases H0–H8 and the larger BOOTMUX architecture remain preserved, but they do not block this path.

---

# Minimal implementation policy

Hackathon V1 favors platform-native capabilities, protocol standards, and small replaceable adapters.

Documentation describes required capabilities rather than naming optional third-party packages. Concrete dependencies may be selected during implementation, pinned in build metadata, and disclosed in the appropriate license or attribution files.

## Dependency budget

```yaml
iphone_app:
  external_runtime_dependencies: 0

firmware:
  allowed_foundation:
    - vendor-supported embedded SDK
    - built-in BLE support
    - built-in USB HID support

companion:
  deployment: single small executable
  external_runtime_services: 0
  third_party_library_budget: minimal

target_agent:
  install_preference:
    - official standalone release
    - official installation route only when a standalone release is unavailable
```

The numbers are implementation constraints, not claims that every component is written from scratch.

## Build-versus-borrow rule

Borrow established behavior for:

- BLE connection management;
- USB HID report handling;
- PTY lifecycle;
- WebSocket framing;
- native text selection and copy;
- UTF-8 handling;
- process launching and exit status;
- virtual-machine execution;
- Codex installation and invocation.

Build only the BOOTMUX-specific contracts:

- committed-text BLE framing;
- message sequence and duplicate suppression;
- keyboard-layout mapping;
- BLE and terminal connection state separation;
- PTY session identity;
- bounded output policy;
- honest sent-input versus observed-output distinction;
- repeatable final proof.

## V1 fast-path rules

1. **Batch committed text.** Send an accepted command as a string or bounded chunks, not as one BLE transaction per character.
2. **Keep control keys separate.** `ENTER`, `BACKSPACE`, `CTRL-C`, stop, and disconnect remain typed control events.
3. **Use a plain terminal view.** V1 renders selectable text; it does not implement a complete terminal emulator.
4. **Batch terminal output.** Flush on newline, a short timer, or a bounded byte threshold rather than updating the phone for every byte.
5. **Prefer one-shot Codex execution.** The final connectivity proof should avoid full-screen interactive terminal behavior.
6. **Avoid extra language runtimes when possible.** Prefer the smallest official Codex distribution supported by the target.
7. **Keep JSON or a tiny readable frame.** Binary codecs and advanced compression are deferred until measurements justify them.
8. **No hidden optimizations.** Every shortcut must preserve the visible V1 claim boundary.

## Immediate rejection rule

A dependency or feature is rejected from V1 when it:

- does not directly close V0, V1, V2, V3, or V4;
- introduces a background service not required by the demo;
- requires a second target operating system;
- replaces a deterministic parser with a model;
- adds full terminal emulation before plain-text copy works;
- adds a new transport before the WebSocket return path is repeatable;
- makes a clean VM restoration harder;
- prevents a single-file or small-bundle Companion deployment.

---

# Current critical path — Hackathon V1

## V0 — Software terminal loop

### Goal

Prove the iPhone terminal interface and Companion before firmware becomes a dependency.

```text
iPhone
↔ local WebSocket
↔ Companion
↔ PTY
```

### Deliverables

- minimal one-screen iPhone app;
- command input field;
- `SEND`, `ENTER`, `BACKSPACE`, and `CTRL-C` actions;
- selectable, read-only terminal output;
- native copy and paste behavior;
- Companion PTY lifecycle;
- local WebSocket transport;
- bounded terminal buffer;
- minimal ANSI sanitization;
- UTF-8-safe output;
- process-exit indication;
- output batching by newline, short interval, or bounded size.

### Implementation constraints

- use platform-native phone APIs wherever available;
- do not add a full terminal emulator;
- do not add authentication, cloud reasoning, or firmware dependencies;
- do not redraw the terminal view for every received byte;
- keep the Companion runnable as one small executable or equivalent minimal bundle.

### Acceptance gate

- `echo BOOTMUX_V0` entered on the iPhone executes in the target PTY;
- `BOOTMUX_V0` appears in the iPhone terminal view;
- the marker can be selected, copied, and pasted;
- disconnect does not crash the app or Companion;
- terminal output is bounded;
- a large synthetic stream does not trigger unbounded UI updates;
- synthetic test output contains no private data.

### Stop rule

Do not wait for ESP32-S3 firmware before closing V0.

---

## V1 — Physical iPhone keyboard path

### Goal

Prove the unique BOOTMUX physical input path.

```text
iPhone
→ BLE GATT
→ ESP32-S3
→ USB HID keyboard
→ target
```

### Deliverables

- BLE GATT input service;
- iPhone BLE connection state;
- ESP32-S3 USB HID keyboard;
- documented baseline keyboard layout;
- committed-text message type;
- bounded chunking based on the negotiated BLE write size;
- sequence and duplicate suppression;
- `ENTER`, `BACKSPACE`, and `CTRL-C` mappings;
- disconnect-safe neutral state;
- emergency output-disable path.

### Implementation constraints

- committed command text is sent in batches rather than one message per key;
- the firmware expands committed text into HID reports locally;
- control events remain distinct from committed text;
- the wire format stays readable and versioned;
- compression, encryption redesign, and advanced multiplexing are deferred;
- only the vendor-supported embedded stack and required protocol components are used.

### Acceptance gate

- a documented ASCII shell command reaches the target correctly;
- one committed input message produces one target command sequence;
- command batching uses fewer BLE writes than per-character delivery;
- reconnect does not replay stale text;
- duplicate delivery does not duplicate committed text;
- `ENTER`, `BACKSPACE`, and `CTRL-C` work;
- emergency stop prevents further HID output;
- no device identifier is written to public logs.

### Explicit exclusions

- mouse and trackpad;
- arbitrary Unicode through HID;
- BLE HID to the target;
- USB data return;
- Wi-Fi firmware features;
- compressed or research transport formats.

---

## V2 — Terminal return to iPhone

### Goal

Return verified target terminal text to the same iPhone interface.

```text
target PTY
→ Companion
→ local WebSocket
→ iPhone terminal view
```

### Deliverables

- stdout and stderr forwarding;
- process-exit event;
- connection-state display separate from BLE state;
- bounded buffering and slow-client behavior;
- plain-text terminal rendering;
- minimal ANSI removal;
- native selection and copy;
- clear distinction between sent input and observed output;
- output coalescing policy;
- bounded reconnect session identifier.

### Output coalescing baseline

A Companion may flush accumulated output when any one condition is met:

```text
newline observed
OR short flush interval elapsed
OR bounded byte threshold reached
OR process exit occurred
```

Exact thresholds are implementation parameters and must be measured rather than promoted as universal constants.

### Implementation constraints

- V2 does not attempt to reproduce full-screen terminal applications;
- raw bytes remain bounded locally long enough to debug sanitization failures;
- WebSocket frames contain text batches or small typed events, not individual characters;
- the phone app appends batches to its model and refreshes the visible view at a bounded rate;
- no advanced semantic compression is required.

### Acceptance gate

- output generated by the target appears on the iPhone;
- stdout and stderr are not silently lost;
- ANSI escape bytes do not appear in copied text;
- an output marker can be selected and copied;
- a large synthetic output remains bounded;
- batching materially reduces WebSocket frames and UI updates relative to per-byte delivery;
- terminal reconnect does not mix different sessions.

### Claim boundary

V2 uses a development WebSocket return path. It does not claim full-duplex terminal transport through ESP32-S3.

---

## V3 — Codex installation bootstrap

### Goal

Use the iPhone-to-S3 HID path to initiate Codex installation in a clean target environment.

### Deliverables

- clean ARM64 Linux VM snapshot or equivalent target;
- documented prerequisite check;
- start-state check showing the tested Codex executable absent;
- smallest supported official installation artifact or official installation route;
- installation command entered through the HID path;
- installation output visible on the iPhone;
- executable-path and version check;
- user-controlled authentication flow;
- redaction and recording rules for authentication output.

### Installation minimization rule

Prefer this order:

```text
official standalone target executable
→ official minimal installer
→ official package-manager route only when required
```

Do not install an additional language runtime solely for BOOTMUX when a supported standalone Codex distribution can satisfy the declared target.

### Acceptance gate

- the test begins from a declared clean snapshot;
- the start state proves the tested Codex executable is absent;
- installation is initiated from iPhone keyboard input through ESP32-S3;
- the installation result is visible in the iPhone terminal;
- the executable and version are verified;
- unnecessary target runtimes are not installed when the selected official distribution does not require them;
- authentication remains user-controlled;
- no credential, token, account identifier, or private local path appears in committed evidence.

### Failure policy

A failed installation is recorded honestly. It must not be described as successful because the command was merely entered.

---

## V4 — Codex connectivity and copy proof

### Goal

Complete the smallest end-to-end BOOTMUX demonstration.

```text
iPhone input
→ ESP32-S3 USB HID
→ Codex on target
→ live terminal output
→ Companion WebSocket
→ iPhone
→ native copy
```

### Invocation rule

The final proof uses a bounded non-interactive or one-shot Codex invocation when supported.

V1 does not need to automate a full-screen Codex terminal UI. Interactive Codex operation remains a later product capability.

### Required sequence

1. restore the clean target snapshot;
2. start Companion;
3. connect the iPhone terminal return path;
4. connect the iPhone to ESP32-S3 over BLE;
5. enter the Codex installation command through USB HID;
6. verify the installed version;
7. complete user-controlled authentication;
8. send a fixed one-shot Codex prompt;
9. receive the fixed response marker `BOOTMUX_READY`;
10. select and copy `BOOTMUX_READY` on the iPhone;
11. paste it into another text field as visible proof;
12. stop or disconnect safely.

### Acceptance gate

- every step is visible or represented by a public-safe evidence record;
- `BOOTMUX_READY` originates from the target Codex process;
- the marker reaches the iPhone terminal view;
- native selection and copy work;
- no full terminal emulator is required for the proof;
- the run can be repeated from the same clean snapshot;
- no hidden manual terminal is used to bypass the demonstrated input path;
- no credentials or personal information appear in the recording;
- failures remain visible and do not become false completion claims.

### V1 completion statement

After this gate, BOOTMUX may claim:

> BOOTMUX used an iPhone and ESP32-S3 as a physical keyboard bootstrap path to install and reach Codex in a clean target environment, then returned live terminal text to the iPhone for native selection and copy.

---

# One-Mac development plan

A single Apple Silicon Mac is sufficient for V1 development.

```text
Mac host
├── phone application development and physical iPhone
├── ESP32-S3 firmware toolchain
└── minimal ARM64 Linux VM
    ├── Companion
    ├── PTY
    └── Codex test installation
```

Recommended constrained guest profile:

```yaml
cpu: 2
memory_gib: 3
disk_gib: 24
graphical_desktop: false
```

## Development lanes

### Lane A — software

```text
iPhone ↔ WebSocket ↔ VM Companion ↔ PTY
```

Close V0 and most of V2 here.

### Lane B — hardware

```text
iPhone → BLE → ESP32-S3 → USB HID → Mac host
```

Close V1 here.

### Lane C — integrated

```text
iPhone → BLE → ESP32-S3 → USB HID → focused VM console
VM Companion → WebSocket → iPhone
```

The VM may receive keyboard input through the focused host window. This is a host-mediated test path and must be described as such.

Direct USB passthrough is optional research and must not block the demo.

---

# Work that may proceed in parallel

Only the following parallelism is allowed before V4:

```text
Track A: phone UI + WebSocket + copy
Track B: Companion PTY + batching + bounded output
Track C: BLE + committed-text framing + USB HID
Track D: clean VM snapshot + minimal Codex installation notes
```

Integration order remains fixed:

```text
A + B
→ V0 and V2

C
→ V1

A + B + C + D
→ V3 and V4
```

Do not begin experimental AI recovery work while any V0–V4 gate remains open.

---

# V1 exclusions

The following are not Hackathon V1 dependencies:

- PAD or trackpad control;
- three-tab UI;
- GPT-5.6 automatic diagnosis;
- autonomous recovery;
- policy-gated mutation engine;
- full Recovery Capsule implementation;
- full Evidence Receipt implementation;
- USB data terminal return;
- Wi-Fi or hotspot routing;
- Windows support;
- multiple target operating systems;
- background iOS relay;
- GPIO power or reset;
- full terminal emulation;
- interactive Codex TUI automation;
- additional local AI models;
- advanced binary codecs;
- EPOCHROOT;
- advanced TTYRETINA;
- SYNDROMUX;
- SYNDCOMP;
- VOIDCODE;
- CAUSALCLOCK;
- STRATAROOT;
- ROOTFIT;
- JANUSPROBE.

Exclusion means “not required before V1 completion,” not removal from the project.

---

# Immediate successor — V1.1

## Goal

Replace the development WebSocket return path with the BOOTMUX bridge.

```text
target Companion
→ USB data interface
→ ESP32-S3
→ BLE
→ iPhone
```

## Entry gate

- V4 is repeatable from a clean snapshot;
- BLE HID input is stable;
- Companion buffering is bounded;
- the iPhone terminal view already handles reconnect and copy.

## Acceptance gate

- target output returns through ESP32-S3;
- control traffic remains available during terminal bursts;
- malformed frames fail closed;
- terminal reconnection does not replay input or mix sessions;
- the WebSocket route is no longer required for the full demonstration.

---

# Post-hackathon product roadmap

The larger BOOTMUX plan resumes only after V1.

## P1 — Product interaction

- PAD, TERMINAL, and AI surfaces;
- trackpad and mouse HID;
- exact Unicode insertion through Companion;
- connection and route controls;
- optional complete terminal emulation when a real use case requires it.

## P2 — Structured execution

- typed tool registry;
- deterministic policy gate;
- approval classes;
- bounded executor;
- machine-generated Evidence Receipts.

## P3 — AI-assisted recovery

- terminal event classification;
- redacted Context Capsules;
- GPT-5.6 Recovery Capsules;
- explicit abstention and failure handling.

## P4 — Target-side Codex handoff

- structured Codex events;
- Handoff Capsule;
- repository-scale task execution;
- persistent session resume.

## P5 — Additional physical management

- Wi-Fi and route selection;
- UART;
- GPIO power and reset;
- signed firmware and Companion releases.

## P6 — Additional platforms

- second target operating system;
- Windows research;
- broader hardware compatibility.

---

# SAI research roadmap

The independent [SAI Research Roadmap](SAI_RESEARCH_ROADMAP.md) remains unchanged as the evidence path for:

```text
H0 measurement and replay
→ H1 TTYRETINA
→ H2 EPOCHROOT
→ H3 SYNDCOMP and SYNDROMUX
→ H4 VOIDCODE
→ H5 CAUSALCLOCK and STRATAROOT
→ H6 ROOTFIT
→ H7 Effect-Bounded Experiment Cell
→ H8 integrated sparse recovery
```

Research work begins only after V1 or in isolated fixtures that cannot delay V0–V4.

Promotion into the product requires:

- deterministic fallback;
- versioned schemas;
- negative safety tests;
- measured improvement or safety value;
- an explicit disable switch;
- honest `SUPPORTED`, `REVISE`, or `REJECTED` status.

---

# Final scheduling rule

Until Hackathon V1 is complete, every proposed task must answer:

> Does this directly close V0, V1, V2, V3, or V4 while staying inside the dependency budget?

If not, it is deferred.
