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
  codex: IMPLEMENTATION_ENGINE
  gpt_5_6: ARCHITECTURE_AND_VERIFICATION_ENGINE
  human: PRODUCT_OWNER_AND_FINAL_AUTHORITY
```

## Central Build Week narrative

> Codex helped build BOOTMUX. BOOTMUX then created a physical first mile that can carry a real Codex workflow into a computer before its normal AI path is ready.

The distinction is deliberate:

```text
Codex
  wrote and repaired major implementation layers

GPT-5.6
  designed contracts, challenged failures, and protected evidence boundaries

Human
  chose the problem, product direction, hardware path, accepted repairs,
  performed physical setup, and owns the final public claims
```

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

physical_result:
  bounded_ascii_hid: OWNER_OBSERVED
  physical_codex_prompt: OWNER_OBSERVED
  bootmux_ready_return_to_iphone: OWNER_OBSERVED
  selectable_copy: PENDING
  clear_feedback: PENDING
  physical_hid_mirror: PENDING
  repeatability: PENDING
```

This ledger records concrete work products and decisions. It does not claim that every roadmap capability is implemented, that GPT-5.6 autonomously owned the project, or that BOOTMUX is production-ready.
