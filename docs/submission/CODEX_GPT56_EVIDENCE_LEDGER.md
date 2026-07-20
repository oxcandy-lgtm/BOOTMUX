# Codex and GPT-5.6 Evidence Ledger

This ledger is public-safe. The Primary Codex Thread is intentionally private; no real Session ID, account information, private URL, screenshot, or private transcript is stored here.

```yaml
primary_codex_thread:
  identifier: PRIVATE
  designation_status: CONFIRMED_BY_OWNER
  confirmed_at: 2026-07-20_JST
  majority_core_work: COMPLETE
  feedback_command_run: true
  feedback_receipt: CAPTURED_PRIVATELY
  feedback_session_id: NOT_STORED_IN_REPOSITORY

build_week_role:
  codex: IMPLEMENTATION_AND_EXECUTION_ENGINE
  gpt_5_6: ARCHITECTURE_REVIEW_AND_CONVERGENCE_ENGINE
  human: PRODUCT_OWNER_PHYSICAL_OPERATOR_AND_FINAL_AUTHORITY

development_method:
  mode: REPEATED_CONVERGENCE_LOOP
  single_prompt_generation: false
  end_condition_driven: true
  implementation_and_proof_separated: true
  false_green_rejected: true
  submission_closeout_included: true
```

## Central Build Week narrative

> Codex helped build BOOTMUX. GPT-5.6 repeatedly decomposed, reviewed, and hardened that implementation. BOOTMUX then created a physical first mile that can carry a real Codex workflow into a computer before its normal AI path is ready.

The distinction is deliberate:

```text
Human
  declares the problem, product direction, and END condition
↓
GPT-5.6
  converts intent into bounded contracts and searches for hidden failure modes
↓
Codex
  implements, runs, tests, and returns concrete repository and runtime evidence
↓
GPT-5.6
  reviews the code and proof, then emits narrow repair instructions
↓
Codex
  repairs and re-validates
↓
Human
  performs physical acceptance or leaves the gate explicitly unresolved
```

This loop continued beyond the first working path into Judge Mode, evidence mapping, privacy boundaries, narrated video planning, and submission closeout. The goal was not maximum code generation. The goal was rapid convergence from an ambiguous idea to a demonstrable END state.

See [Codex + GPT-5.6 Development Loop](CODEX_GPT56_DEVELOPMENT_LOOP.md) for the full public-safe workflow.

## Why the loop accelerated development

The loop allowed one human builder to coordinate several normally separate engineering domains inside the Build Week period:

```text
Go + PTY + WebSocket
SwiftUI + CoreBluetooth
ESP32-S3 + BLE + USB HID
ARM64 VM + official Codex CLI
Judge Mode + evidence + narrated submission
```

No exact hour-count claim is made. The defensible acceleration claim is that Codex implementation velocity, GPT-5.6 review pressure, and human scope control compressed a multi-domain development process into the submission period without treating unverified work as complete.

## Contribution record

| Contributor / use | Task or decision | Resulting commits or files | Concrete result | Human decision boundary |
| --- | --- | --- | --- | --- |
| Codex primary implementation | built the Go Companion, PTY/WebSocket protocol, bounded lifecycle, local Judge Mode, and tests | `companion/`; V0A through R3 commits | working non-trivial target-side terminal core | human selected the scope and accepted the implementation gates |
| Codex native client implementation | built the dependency-free SwiftUI iPhone client, selectable output bridge, WebSocket transport, controls, reconnect logic, and tests | `iphone/`; V0B and repair commits | native iPhone terminal and CODEX/HID surfaces | human handled signing, device trust, physical installation, and acceptance |
| Codex firmware implementation | built and repaired the BLE GATT to ESP32-S3 USB HID path, bounded frames, acknowledgements, duplicate handling, and safety controls | `firmware/esp32s3-bridge/`; V1 commits | bounded physical ASCII keyboard path | human selected the hardware direction and performed real-device wiring and observation |
| Codex VM and bootstrap implementation | built the ARM64 Lima harness, Companion provisioning, official Codex installation path, forwarder, and bounded Codex adapter | `vm/`; `tools/bootmux_tcp_forward.py`; `companion/codex.go` | clean-VM Codex installation and `BOOTMUX_READY` probes | human performed authentication and approved the physical end-to-end run |
| GPT-5.6-assisted architecture | separated physical input from independently observed target output | `README.md`; `docs/ARCHITECTURE.md`; protocol documents | asymmetric first-mile architecture that does not treat sent input as observed output | human chose BOOTMUX as the product and retained the hardware boundary |
| GPT-5.6-assisted implementation contract | defined versioned messages, bounded history, queue limits, output batching, and fail-closed lifecycle expectations | V0A and V0B implementation history | converted the concept into testable implementation gates | human approved which contracts were required for the hackathon slice |
| GPT-5.6-assisted adversarial review | reviewed PTY lifecycle, writer shutdown, overflow, UTF-8, interrupts, background behavior, reconnect isolation, and stale output risks | V0A R1–R3; V0B R1–R2 | repaired edge cases that a happy-path demo would not expose | human accepted fixes and preserved unresolved physical gates |
| GPT-5.6-assisted BLE review | identified unsafe non-trivial `String` ownership inside the FreeRTOS queue and directed bounded POD-owned frames | `0fed277`; firmware and V1 evidence | removed the primary BLE queue ownership hazard; observed short transport became stable | human performed firmware upload and physical transport observation |
| GPT-5.6-assisted evidence design | separated code-green, VM-observed, owner-observed, and still-unproven states | `docs/submission/CLAIM_EVIDENCE_MATRIX.md`; evidence receipts | prevented Judge Mode or sent input from becoming false physical proof | human remains responsible for all final public claims |
| GPT-5.6-assisted submission design | selected the Developer Tools positioning, no-rebuild Judge Mode, three-minute narrative, and Codex/GPT-5.6 evidence spine | `README.md`; `judge/`; `docs/submission/` | made the project reviewable without requiring judges to own the hardware | human owns narration, video edit, registration, and submission |
| GPT-5.6-assisted R4 physical-demo review | specified endpoint persistence, COPY ALL/CLEAR/FOLLOW, ASCII fail-fast, physical launcher, and read-only HID Mirror | `243806f04b58ed2f5716440f89b648e17cdd32d2` | strengthened the physical-demo and judge-facing usability paths | human must physically confirm Mirror, copy, CLEAR, and repeatability |
| GPT-5.6-assisted R4R1 path audit | detected that the launcher and HID target could resolve different transcript paths and that replace-under-open-writer trimming was unsafe | `08b7d02a8a1e0309c71cb03db74bc6f1701c434c`; `vm/run-physical-demo.sh`; `vm/start-hid-target.sh` | unified the VM transcript path and changed the bound to explicit fail-closed behavior | human must run the final Lima and physical Mirror acceptance |
| Human product and physical work | identified the dirty-display/bootstrap problem, selected iPhone + ESP32-S3, wired devices, signed and installed the app, authenticated Codex, recorded physical evidence, and directed final scope | physical receipts and owner confirmations | real iPhone → BLE/forwarder/VM → Codex → `BOOTMUX_READY` return | the owner retains final authority and responsibility |

## Concrete convergence examples

### Companion lifecycle

Codex implemented the Companion. GPT-5.6 reviewed timer behavior, PTY synchronization, process reaping, outbound close ownership, overflow, UTF-8, interrupts, and descendant cleanup. Codex then repaired and re-ran tests, race checks, stress loops, builds, and probes across V0A R1–R3.

### BLE queue ownership

A physical transport failure was not patched at the UI. GPT-5.6 traced it to non-trivial `String` ownership in a raw-copy FreeRTOS queue. Codex replaced it with bounded POD-owned frames and explicit overflow behavior, after which the observed short run completed without the prior disconnect.

### HID Mirror path binding

Codex implemented the physical launcher and Mirror path. GPT-5.6 reviewed the real file and process relationships, found mismatched VM path expansion and stale-writer risk, and issued a bounded repair. Codex unified the transcript path and changed over-limit behavior to fail closed.

These are evidence of the repeated pattern:

```text
implementation → evidence → independent review → bounded repair → re-validation
```

## Current evidenced outcome

```yaml
codex_built_layers:
  companion: true
  iphone_client: true
  esp32_firmware: true
  vm_harness: true
  codex_adapter: true
  judge_mode: true
  tests_and_repairs: true

gpt_5_6_material_contribution:
  asymmetric_architecture: true
  bounded_contracts: true
  adversarial_review: true
  ble_queue_repair: true
  evidence_boundaries: true
  hid_mirror_path_audit: true
  submission_strategy: true
  convergence_control: true

physical_result:
  bounded_ascii_hid: OWNER_OBSERVED
  physical_codex_prompt: OWNER_OBSERVED
  bootmux_ready_return_to_iphone: OWNER_OBSERVED
  selectable_copy: PENDING
  clear_feedback: PENDING
  physical_hid_mirror: PENDING
  repeatability: PENDING
```

This ledger records concrete work products and decisions. It does not claim that every roadmap capability is implemented, that GPT-5.6 autonomously owned the project, that an exact development-hour count was independently measured, or that BOOTMUX is production-ready.
