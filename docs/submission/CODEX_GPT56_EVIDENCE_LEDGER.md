# Codex and GPT-5.6 Evidence Ledger

This ledger is public-safe. The primary Codex thread is intentionally private; no real Session ID, account information, private URL, screenshot, or transcript is stored here.

```yaml
primary_codex_thread:
  identifier: PRIVATE
  designation_status: CONFIRMED_BY_OWNER
  confirmed_at: 2026-07-20_JST
  majority_core_work: IN_PROGRESS
  feedback_command_run: false
  feedback_session_id: NOT_STORED_IN_REPOSITORY
```

## Contribution record

| Contributor / use | Task or decision | Resulting commit or files | Concrete result | Human decision boundary |
| --- | --- | --- | --- | --- |
| GPT-5.6-assisted architecture | separated asymmetric transport roles: iPhone input, BLE transport, ESP32-S3 USB HID, target-side Companion, and terminal return | V0A implementation history; `README.md`; `docs/ARCHITECTURE.md` | kept the target-side return path independent from the future physical input path | human selected the product scope and hardware direction |
| GPT-5.6-assisted implementation contract | defined the V0A versioned WebSocket/PTy/session contract and public-safe failure boundaries | `7854781a69d6bc0d93e7759ba8aa467e5b0e2a04`; `companion/` | produced the locally testable Companion Core | human approved the V0A gate and repository boundary |
| GPT-5.6-assisted code review | reviewed V0A R1–R3 lifecycle, overflow, UTF-8, interrupt, input bounds, origin, and shutdown edge cases | `6099662d7e146ba250381df33b3aea14a995e3e7`; `9ff5766e17276df367f8a1219ebc992eab82765b`; `2f9378f0d84ce0b3cb0caabdd9229a8ae7f0b2d4` | tightened the production Companion contract and local verification evidence | human retained authority over which fixes were accepted and what remained unproven |
| GPT-5.6-assisted claim review | established a public claim-safety boundary | `docs/submission/CLAIM_EVIDENCE_MATRIX.md`; `docs/PUBLICATION_SAFETY.md` | prevents unproven iPhone, BLE, USB HID, mouse, offline, Codex, and post-boot claims from being presented as complete | human must confirm final public claims |
| GPT-5.6-assisted submission writing | structured Devpost short copy and story support around the actual architecture and evidence boundary | `bf74c4d5d30f41d0a7df69f93a0929d6588e0416`; `docs/submission/DEVPOST_COPY_AND_STORY_DRAFT.md` | created a working draft while retaining explicit placeholders for unproven capabilities | human owns final wording, attribution, registration, license, and submission |
| GPT-5.6-assisted V0B implementation | defined the native one-screen SwiftUI scope, asymmetric transport boundary, bounded terminal history, UI coalescing, streaming ANSI sanitization, and session-isolated reconnect contract | `2d730a5a287166a889e26e0067f2d518327390d1`; `iphone/` | added the dependency-free iPhone terminal loop and production `URLSessionWebSocketTask` transport; physical proof remains pending | human confirmed this thread as Primary Codex Thread and must complete physical acceptance |
| S81 submission closeout | narrowed the public submission slice, repaired launcher readiness and cleanup, prepared the 171-character description, owner-story working draft, and narrated video order | `41755062060c2aa3b828dd9d9eb675074ff941ef`; `README.md`; `docs/submission/` | submission package is ready for `/feedback`, video, and human review; Xcode and physical proof remain pending | owner must run `/feedback` and complete final submission review |
| GPT-5.6-assisted V0B R1 repair | reviewed normal-exit termination, strict output bounds, CRLF streaming state, injected transport tests, background cleanup, typed close, CLEAR invalidation, and selectable-text updates | `d9746c818eabc31b8bc6bf50c44ecdcbd3dbf395`; `iphone/` | repaired the client runtime contract without changing the physical-proof claim | human must complete Xcode and physical iPhone acceptance |
| GPT-5.6-assisted V0B R2 repair | reviewed the single protocol-limit contract, input/JSON/WebSocket bounds, bounded typed-close timeout, error finalization, selection clamping, deterministic fake transport tests, and Xcode-host inventory boundary | `f554b38a5e0c5218c98f0811b7b8667bd379a32e`; `iphone/` | completed the code-side contract repair; Xcode and physical proof remain unverified because Xcode is not installed on the validation host | human must provide Xcode/Simulator and physical iPhone acceptance |
| GPT-5.6-assisted Submission Sprint | prioritized a no-rebuild Judge Mode, explicit MIT/readme boundary, honest claim matrix, Devpost final draft, demo script, and final checklist over deferred product completeness | current Submission Sprint docs and `judge/` | made the working terminal-and-copy path reviewable without claiming BLE, USB HID, or Codex completion | human owns final registration, feedback, video, and submission |

This record describes concrete work products and decisions; it is not a claim that every future capability is implemented.

| GPT-5.6-assisted V1 R3 acceptance repair | repaired native USB descriptor initialization and iOS project SDK targeting; executed Xcode, USB, firmware, and physical-device checks within the available host boundary | `8fb241b`; `firmware/esp32s3-bridge/src/main.cpp`; `iphone/BOOTMUX.xcodeproj/project.pbxproj` | code-side repair is recorded; native HID enumeration and physical iPhone acceptance remain unproven | human must provide a usable COM flash path, iOS platform/device, and physical acceptance receipt |
