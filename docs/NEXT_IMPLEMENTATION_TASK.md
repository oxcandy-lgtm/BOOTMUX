# BOOTMUX Next Implementation Task — V0A Companion Core

## Status

```yaml
status: READY_FOR_IMPLEMENTATION
task_id: BOOTMUX-V0A-COMPANION-CORE
technical_gate: V0
submission_gate_support:
  - BW1
  - BW2
  - BW3
pull_request: 1
branch: agent/bootstrap-design-roadmap
```

This is the first implementation task for BOOTMUX.

The repository currently contains architecture and roadmap documents but no runtime implementation. V0A creates the smallest locally testable target-side terminal loop before the iPhone application or ESP32-S3 firmware becomes a dependency.

---

# Non-negotiable operating policy

## GitHub Issues are prohibited

Do not read, search, create, edit, comment on, label, assign, close, reopen, react to, or otherwise access GitHub Issues.

Do not use an Issue as a progress log, evidence store, task tracker, or Pull Request source.

Do not call issue-related GitHub APIs or issue-related CLI commands.

## GitHub Actions are unavailable and prohibited

Do not create, edit, enable, trigger, rerun, inspect, or depend on GitHub Actions workflows.

Do not add files under `.github/workflows/`.

Do not claim CI success.

All completion evidence must come from local commands executed by the code implementer and from exact remote-head verification after push.

## Pull Request boundary

Use only the existing Draft Pull Request #1 and its existing branch.

Allowed:

- read the repository and Draft PR #1;
- modify files required by this task;
- commit and push to `agent/bootstrap-design-roadmap`;
- update the existing PR body when required;
- read PR metadata and the final diff;
- verify the final remote head SHA.

Prohibited:

- creating another Pull Request;
- merging PR #1;
- marking PR #1 ready for review;
- closing PR #1;
- force-pushing or rewriting published history;
- pushing directly to `main`;
- creating releases or tags;
- posting unsolicited PR comments.

---

# Goal

Create a small target-side Companion that proves this loop without requiring iPhone or ESP32-S3 hardware:

```text
local probe client
→ WebSocket
→ BOOTMUX Companion
→ PTY-hosted shell process
→ batched observed output
→ local probe client
```

The task closes only the target-side foundation of V0. It does not claim that the physical phone, BLE, USB HID, Codex installation, or complete V0 user experience is finished.

---

# Required implementation

## 1. Repository structure

Create a minimal `companion/` implementation with:

- one small deployable executable or equivalent minimal bundle;
- a documented build command;
- a documented local run command;
- a local probe or integration-test client;
- unit and integration tests;
- pinned implementation dependencies;
- attribution or notice updates when required by selected dependency licenses.

Do not create iPhone or firmware scaffolding in this task.

## 2. Companion process

The Companion must:

- run on the declared initial Unix-like target environment;
- start one PTY-hosted shell process using an explicit executable and argument list;
- expose one versioned WebSocket terminal endpoint;
- bind to loopback by default;
- require an explicit flag or configuration to bind beyond loopback;
- generate a fresh opaque session identifier per PTY session;
- forward accepted client input to the PTY;
- forward observed PTY output to the connected client;
- report process exit status;
- close the PTY and child process cleanly;
- reject malformed or unsupported messages;
- avoid shell interpolation when starting the PTY process;
- avoid persistent background-service installation.

The implementation may select small maintained PTY and WebSocket libraries. The public architecture must continue to describe capabilities rather than making a temporary package name part of the BOOTMUX product claim.

## 3. Versioned message contract

Use a readable and versioned message format.

Minimum client-to-server message types:

```json
{"v":1,"type":"input_text","session_id":"opaque","text":"echo BOOTMUX_V0A\n"}
{"v":1,"type":"control","session_id":"opaque","control":"interrupt"}
{"v":1,"type":"close","session_id":"opaque"}
```

Minimum server-to-client message types:

```json
{"v":1,"type":"hello","session_id":"opaque"}
{"v":1,"type":"output","session_id":"opaque","stream":"pty","text":"..."}
{"v":1,"type":"exit","session_id":"opaque","exit_code":0}
{"v":1,"type":"error","session_id":"opaque-or-empty","code":"...","message":"public-safe"}
```

Exact field names may change only when the implementation documents the final schema and tests it.

Requirements:

- unsupported protocol versions fail closed;
- an input message for the wrong session is rejected;
- input and observed output remain distinguishable;
- server output is never synthesized from the sent input and mislabeled as target output;
- errors do not expose local absolute paths, environment secrets, account identifiers, or raw private configuration.

## 4. Bounded output and batching

Do not send one WebSocket frame for every PTY byte.

Output may be flushed when any one condition is met:

```text
newline observed
OR short bounded interval elapsed
OR bounded byte threshold reached
OR process exit occurred
```

Requirements:

- thresholds are named configuration values rather than unexplained magic constants;
- visible or retained output has a strict upper bound;
- slow clients cannot create unbounded memory growth;
- buffer overflow behavior is explicit and tested;
- UTF-8 boundaries are preserved or invalid sequences are handled deterministically;
- process exit flushes pending output;
- reconnect cannot mix output from different PTY sessions.

## 5. Local probe

Provide a local probe that can execute the acceptance sequence without iPhone or ESP32-S3 hardware.

The probe must:

1. start or connect to the Companion on loopback;
2. receive the session identifier;
3. send a command that causes the target process to emit `BOOTMUX_V0A`;
4. receive `BOOTMUX_V0A` as observed PTY output;
5. record the exit event or close the session cleanly;
6. return a nonzero exit code on protocol, timeout, output, or process failure.

The probe is development evidence only. It must not be described as proof of the BLE or USB HID path.

---

# Required tests

At minimum, add real tests for:

- protocol version rejection;
- malformed JSON or malformed message rejection;
- wrong-session rejection;
- successful PTY command and observed output;
- process exit event;
- interrupt control behavior;
- output batching that produces fewer frames than per-byte delivery for a multi-byte fixture;
- output-buffer upper bound;
- slow-client or backpressure handling;
- UTF-8 split across read boundaries;
- reconnect or new-session isolation;
- child-process cleanup after client close;
- public-safe error output.

Tests must exercise the production implementation. A duplicate fake implementation used only by tests is not acceptable.

---

# Local validation only

GitHub Actions must not be used.

Run the strongest applicable local checks, including at minimum:

```text
format check
static analysis or vet equivalent
unit tests
integration tests
clean build
git diff --check
complete final diff inspection
public-safety scan or equivalent repository search
exact remote-head verification after push
```

Record the exact commands and actual results.

A missing tool or unsupported environment is a YELLOW blocker, not a pass.

Do not install a persistent service or mutate the host outside the repository and temporary test directories.

---

# Explicitly deferred

Do not implement any of the following in V0A:

- iPhone UI;
- BLE;
- ESP32-S3 firmware;
- USB HID;
- mouse or trackpad input;
- Codex installation or authentication;
- GPT-5.6 runtime calls;
- complete terminal emulation;
- advanced semantic terminal parsing;
- Policy Gate;
- Recovery Capsules;
- Evidence Receipts beyond the local test report;
- SAI research mechanisms;
- Windows support;
- daemon or service installation;
- GitHub Actions;
- GitHub Issues.

---

# ESP32-S3 real-hardware evidence gate

Real ESP32-S3 data is required before V1 can be declared complete, but it must not block V0A.

Before firmware implementation is accepted, create a hardware evidence record containing public-safe values for:

- exact development-board model and hardware revision;
- exact module variant when visible from the board or vendor documentation;
- which physical connector exposes native ESP32-S3 USB rather than only a USB-to-UART bridge;
- confirmation that the cable carries data;
- host operating system used for enumeration;
- actual USB HID enumeration result;
- actual negotiated BLE ATT MTU or phone-reported maximum write length;
- actual committed-text chunk size;
- BLE write count for a fixed command;
- observed command latency;
- duplicate-suppression result;
- reconnect stale-input result;
- emergency-stop result;
- tested keyboard layout and target console layout;
- firmware, app, and Companion build identifiers.

Do not record or publish:

- Bluetooth MAC addresses;
- USB serial numbers;
- account identifiers;
- private hostnames;
- local absolute user paths;
- authentication material.

The board profile remains `UNRESOLVED` until the exact physical board is known. Do not hard-code assumptions from a generic ESP32-S3 board into V1 completion claims.

Official implementation facts that may guide later V1 work:

- ESP32-S3 supports USB device functions including HID and composite devices through the vendor-supported USB device stack;
- native USB D+ and D- are routed through GPIO20 and GPIO19 at chip level;
- development boards with multiple USB connectors may expose native USB on a connector distinct from the USB-to-UART connector;
- ESP32-S3 supports Bluetooth LE, and the lighter BLE-only host stack is available in the vendor SDK;
- negotiated BLE payload capacity must be measured on the real phone-board connection rather than assumed from a constant.

Official references:

- https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/usb_device.html
- https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/ble/overview.html
- https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/kconfig-reference.html
- https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html

---

# Required final PR update

After implementation and push, update the existing Draft PR body with:

- task ID;
- starting and final head SHA;
- implementation summary;
- changed-file list;
- exact local validation commands and outcomes;
- explicit statement that GitHub Actions were not used;
- explicit statement that GitHub Issues were not accessed or modified;
- limitations and deferred scope;
- current V0 gate status;
- current ESP32-S3 hardware-evidence status;
- public-safety review.

Keep the PR Draft, open, and unmerged.

---

# Final report contract

Return one structured report:

```yaml
repository: oxcandy-lgtm/BOOTMUX
pull_request: 1
branch: agent/bootstrap-design-roadmap
task_id: BOOTMUX-V0A-COMPANION-CORE
starting_head_sha:
final_head_sha:

pull_request_state:
  open:
  draft:
  merged:
  ready_for_review:

implementation:
  companion_core:
  pty_session:
  websocket_endpoint:
  protocol_v1:
  bounded_output:
  batching:
  local_probe:

changed_files:
  count:
  paths:

validation:
  format:
  static_analysis:
  unit_tests:
  integration_tests:
  clean_build:
  git_diff_check:
  public_safety:
  exact_remote_head_verified:

github_actions:
  used: false
  workflow_files_added: false
  dependency_on_actions: false

github_issues:
  read: false
  searched: false
  created: false
  edited: false
  commented: false
  api_used: false

esp32s3_hardware:
  required_for_v0a: false
  required_before_v1_completion: true
  exact_board_resolved:
  evidence_status:

blockers:
  implementation:
  environment:
  hardware:
  submission:

classification:
```

Allowed classifications:

```text
GREEN_V0A_COMPANION_CORE_IMPLEMENTED_AND_LOCALLY_VERIFIED
YELLOW_V0A_IMPLEMENTED_WITH_ENVIRONMENTAL_VALIDATION_BLOCKER
RED_V0A_IMPLEMENTATION_OR_CONTRACT_FAILURE
```

Use GREEN only when the implementation is committed, pushed, locally validated, exact-head verified, and the existing Draft PR remains open and unmerged.
