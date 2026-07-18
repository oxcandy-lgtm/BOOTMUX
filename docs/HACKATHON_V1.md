# BOOTMUX Hackathon V1

## Purpose

Hackathon V1 proves one narrow BOOTMUX claim:

> An iPhone can create a physical keyboard path into a target environment, bootstrap Codex there, receive the resulting terminal stream, and make that output selectable and copyable on the phone.

This version is intentionally smaller than the full BOOTMUX architecture. It is a vertical proof, not a production management platform.

## Exact completion contract

V1 is complete only when all three user-visible capabilities work in one repeatable demonstration:

1. **iPhone keyboard input** reaches the target through BLE and ESP32-S3 USB HID.
2. **Codex installation and connectivity** are initiated from that input path and verified on the target.
3. **Terminal text returns to the iPhone** and can be selected and copied with native iOS behavior.

The final demonstration prompt should produce a fixed marker such as:

```text
BOOTMUX_READY
```

The marker must appear in the iPhone terminal view and be copyable into another text field.

## V1 system boundary

```text
Input path:

iPhone text entry
→ BLE GATT
→ ESP32-S3
→ USB HID keyboard
→ target terminal

Output path:

target PTY
→ BOOTMUX Companion
→ local WebSocket
→ iPhone terminal view
```

The asymmetric transport is deliberate.

- The input path proves the physical BOOTMUX bridge.
- The WebSocket output path keeps the first implementation small and observable.
- Returning terminal output through USB data and ESP32-S3 BLE is deferred to V1.1.

V1 must not imply that its terminal return path is already out-of-band or carried through ESP32-S3.

## Minimal-dependency contract

Hackathon V1 describes capabilities instead of prescribing optional third-party packages.

Implementation choices should prefer:

1. platform-native phone APIs;
2. vendor-supported embedded SDK components;
3. one small Companion executable or minimal bundle;
4. official Codex distribution channels;
5. readable, versioned protocols;
6. deterministic code over model-based parsing.

Concrete dependencies may be selected during implementation, pinned in build metadata, and disclosed in the appropriate attribution files. A dependency name does not belong in the V1 architecture unless the implementation cannot be described accurately without it.

### Dependency budget

```yaml
iphone_app:
  external_runtime_dependencies: 0

firmware:
  foundation:
    - vendor-supported BLE support
    - vendor-supported USB HID support

companion:
  external_runtime_services: 0
  deployment: one small executable or equivalent minimal bundle
  optional_libraries: keep to the minimum needed for PTY and WebSocket behavior

target_agent:
  source: official distribution only
```

### V1 optimization rules

- send committed text in bounded batches instead of one BLE transaction per character;
- keep `ENTER`, `BACKSPACE`, `CTRL-C`, stop, and disconnect as separate control events;
- expand committed text into USB HID reports on ESP32-S3;
- send PTY output in batches rather than one WebSocket frame per byte;
- update the visible terminal at a bounded rate;
- use selectable plain text instead of a complete terminal emulator;
- prefer a one-shot Codex invocation for the final proof;
- avoid installing an additional language runtime when a supported official standalone Codex distribution is available;
- keep the initial protocol readable instead of introducing an advanced binary codec;
- measure before adding compression or research transport features.

## Minimal components

### iPhone application

One primary screen is sufficient.

```text
┌──────────────────────────┐
│ BOOTMUX        CONNECTED │
├──────────────────────────┤
│ selectable terminal text │
│                          │
│ $ codex --version        │
│ BOOTMUX_READY            │
│                          │
├──────────────────────────┤
│ command input            │
│ [____________________]   │
│ [SEND] [ENTER] [CTRL-C]  │
└──────────────────────────┘
```

Required:

- BLE connection to ESP32-S3;
- local WebSocket connection to Companion;
- command text entry;
- committed-text batching;
- `SEND`, `ENTER`, `BACKSPACE`, and `CTRL-C` actions;
- connection state for both BLE and terminal return paths;
- read-only, selectable terminal text;
- native iOS copy behavior;
- bounded visible terminal history;
- bounded UI refresh frequency;
- explicit disconnect or stop control.

Not required:

- PAD tab;
- AI tab;
- full terminal emulation;
- arbitrary Unicode through Stage 0 HID;
- automatic recovery UI;
- background operation;
- third-party phone runtime libraries.

### ESP32-S3 firmware

Required:

- custom BLE GATT input service;
- USB HID keyboard output;
- committed-text message type;
- bounded text chunk reassembly;
- sequence and duplicate suppression;
- mapping for the documented baseline keyboard layout;
- `ENTER`, `BACKSPACE`, and `CTRL-C` support;
- disconnect-safe neutral state;
- emergency stop or output-disable command;
- no replay of stale input after reconnect.

Not required:

- USB mouse;
- USB data return path;
- BLE HID to the target;
- Wi-Fi;
- compression;
- advanced multiplexing;
- persistent recovery capsules;
- GPIO or power control.

### BOOTMUX Companion

Required:

- one supported target environment;
- PTY creation and lifecycle management;
- WebSocket endpoint bound to the local development network;
- forwarding of PTY output to the iPhone;
- output batching on newline, short interval, bounded size, or process exit;
- bounded buffering and slow-client handling;
- ANSI sanitization suitable for a plain-text V1 view;
- UTF-8-safe output;
- process exit indication;
- session identity that prevents reconnect mixing;
- synthetic public-safe logs for tests;
- minimal deployment footprint.

V1 does not require a general structured executor, policy engine, cross-platform abstraction, full terminal emulator, model-based parser, or persistent background service.

### Codex bootstrap

Required proof sequence:

1. confirm that the selected clean target snapshot does not already contain the tested Codex installation;
2. select the smallest supported official Codex installation artifact or route;
3. enter the documented installation command through the iPhone-to-S3 HID path;
4. observe installation progress or result in the iPhone terminal view;
5. verify the installed executable and version;
6. complete authentication through a user-controlled flow;
7. send one fixed, bounded, preferably non-interactive connectivity prompt;
8. receive the fixed response marker on the iPhone;
9. copy that marker using native iOS selection.

Authentication secrets must not be transported to the iPhone terminal view, committed to fixtures, or included in recordings.

## Development topology with one Mac

A single Mac can host the entire development setup.

```text
Mac host
├── phone application development and physical iPhone
├── ESP32-S3 firmware toolchain
└── ARM64 Linux virtual machine
    ├── BOOTMUX Companion
    ├── shell / PTY
    └── Codex test installation
```

Recommended guest profile for a constrained Apple Silicon Mac:

```yaml
guest: minimal ARM64 Linux server
cpu: 2
memory_gib: 3
disk_gib: 24
graphical_desktop: false
```

### Development lanes

#### Lane A — software loop

```text
iPhone
↔ WebSocket
↔ Companion in VM
↔ PTY
```

Purpose:

- finish the iPhone terminal view;
- validate copy and paste;
- validate PTY streaming and batching;
- test Codex installation without waiting for firmware.

#### Lane B — hardware input

```text
iPhone
→ BLE
→ ESP32-S3
→ USB HID
→ Mac host
```

Purpose:

- validate committed-text framing;
- validate keyboard mapping;
- validate duplicate suppression and stop behavior;
- measure BLE writes against a per-character baseline.

#### Lane C — integrated V1

```text
iPhone
→ BLE
→ ESP32-S3
→ USB HID
→ focused VM console

VM Companion
→ WebSocket
→ iPhone
```

The VM window may receive HID through the Mac host during development. This must be documented honestly as a host-mediated test path rather than direct USB passthrough.

Direct ESP32-S3 USB passthrough into a VM may be researched, but it must not block V1.

## V1 evidence package

A successful run should produce public-safe evidence containing:

- V1 version and commit;
- iPhone app build identifier;
- firmware build identifier;
- Companion build identifier;
- target guest OS and architecture using generic values;
- start state showing the tested Codex executable absent;
- committed-text message count;
- BLE write count;
- duplicate-suppression result;
- terminal batch and frame counts;
- terminal connection state;
- Codex version output;
- fixed connectivity response marker;
- confirmation that the marker was copied;
- any failure classification stated honestly.

Do not publish authentication tokens, account identifiers, real hostnames, local user paths, device identifiers, or unredacted terminal history.

## Explicit V1 exclusions

The following are preserved in the full architecture and research roadmap but are not implementation dependencies for Hackathon V1:

- pointer or trackpad control;
- three-tab product UI;
- GPT-5.6 automatic diagnosis;
- policy-gated autonomous repair;
- Recovery Capsules and Evidence Receipts beyond simple demo records;
- EPOCHROOT;
- TTYRETINA beyond minimal ANSI-safe plain text;
- SYNDROMUX and SYNDCOMP;
- VOIDCODE;
- CAUSALCLOCK and STRATAROOT;
- ROOTFIT;
- JANUSPROBE;
- USB data terminal return;
- complete terminal emulation;
- interactive full-screen Codex automation;
- advanced binary codecs;
- additional local AI models;
- Windows support;
- multiple target operating systems;
- GPIO power and reset;
- unattended production administration.

## Promotion to V1.1

V1.1 replaces the development WebSocket return path with:

```text
target Companion
→ USB data interface
→ ESP32-S3
→ BLE
→ iPhone
```

V1.1 begins only after V1 is repeatable from a clean VM snapshot.

## Final claim boundary

A completed Hackathon V1 may claim:

> BOOTMUX used an iPhone and ESP32-S3 as a physical keyboard bootstrap path to install and reach Codex in a clean target environment, then returned the live terminal text to the iPhone for native selection and copy.

It may not yet claim:

- a complete out-of-band full-duplex terminal through ESP32-S3;
- autonomous machine recovery;
- production-grade isolation or security;
- validated SAI research optimizations;
- universal target support.