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
- Returning terminal output through USB CDC and ESP32-S3 BLE is deferred to V1.1.

V1 must not imply that its terminal return path is already out-of-band or carried through ESP32-S3.

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
- `SEND`, `ENTER`, `BACKSPACE`, and `CTRL-C` actions;
- connection state for both BLE and terminal return paths;
- read-only, selectable terminal text;
- native iOS copy behavior;
- bounded visible terminal history;
- explicit disconnect or stop control.

Not required:

- PAD tab;
- AI tab;
- full terminal emulation;
- arbitrary Unicode through Stage 0 HID;
- automatic recovery UI;
- background operation.

### ESP32-S3 firmware

Required:

- custom BLE GATT input service;
- USB HID keyboard output;
- sequence number or duplicate suppression for committed input messages;
- mapping for the documented baseline keyboard layout;
- `ENTER`, `BACKSPACE`, and `CTRL-C` support;
- disconnect-safe neutral state;
- emergency stop or output-disable command;
- no replay of stale input after reconnect.

Not required:

- USB mouse;
- USB CDC return path;
- BLE HID to the target;
- Wi-Fi;
- persistent recovery capsules;
- GPIO or power control.

### BOOTMUX Companion

Required:

- one supported target environment;
- PTY creation and lifecycle management;
- WebSocket endpoint bound to the local development network;
- forwarding of PTY output to the iPhone;
- bounded buffering and slow-client handling;
- ANSI sanitization suitable for a plain-text V1 view;
- UTF-8-safe output;
- process exit indication;
- synthetic public-safe logs for tests.

V1 does not require a general structured executor, policy engine, or cross-platform abstraction.

### Codex bootstrap

Required proof sequence:

1. confirm that the selected clean target snapshot does not already contain the tested Codex installation;
2. enter the documented installation command through the iPhone-to-S3 HID path;
3. observe installation progress or result in the iPhone terminal view;
4. verify the installed executable and version;
5. complete authentication through a user-controlled flow;
6. send one fixed connectivity prompt;
7. receive the fixed response marker on the iPhone;
8. copy that marker using native iOS selection.

Authentication secrets must not be transported to the iPhone terminal view, committed to fixtures, or included in recordings.

## Development topology with one Mac

A single Mac can host the entire development setup.

```text
Mac host
├── Xcode and physical iPhone
├── ESP32-S3 toolchain
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
- validate PTY streaming;
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

- validate BLE framing;
- validate keyboard mapping;
- validate duplicate suppression and stop behavior.

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
- HID input receipt counters without raw personal text;
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
- USB CDC terminal return;
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
