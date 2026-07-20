# OpenAI Build Week Requirements for BOOTMUX

## Verification status

```yaml
verified_at: 2026-07-21_JST
competition: OpenAI Build Week
recommended_track: Developer Tools
source_of_truth: https://openai.devpost.com/rules
supporting_faq: https://openai.devpost.com/details/faqs
submission_deadline:
  pacific: 2026-07-21T17:00:00-07:00
  japan: 2026-07-22T09:00:00+09:00
```

This page is an operational summary for BOOTMUX. The Official Rules control whenever any project document, FAQ, plugin output, or community post conflicts with them.

## Purpose of the competition

OpenAI Build Week asks entrants to create a real, working project with **Codex and GPT-5.6**. The project may be an application, agent, workflow, game, backend system, plugin, or developer tool, but it must go beyond a decorative AI reference: the implementation must be non-trivial, runnable, and clearly demonstrate how Codex and GPT-5.6 contributed.

Operationally, the event is testing whether builders can use Codex and GPT-5.6 as serious collaborators to turn an idea into a coherent product during the Submission Period, while preserving human ownership of the problem, product choices, engineering decisions, and final claims.

Sources:

- [Official Rules — Project Requirements and Judging](https://openai.devpost.com/rules)
- [Official FAQ — required tools and submission package](https://openai.devpost.com/details/faqs)
- [Official Build Week update — what to build](https://openai.devpost.com/updates/45282-openai-build-week-submissions-are-open-plugin-launch)

## Main regulations

### 1. Required technology

- The project must be built with **Codex and GPT-5.6**.
- Codex use must be visible in the text description, README, and narrated demo.
- GPT-5.6 use must be meaningful rather than incidental or decorative.
- GPT-5.6 does not need to be used for every task, and the runtime is not required to call the OpenAI API merely to satisfy the build requirement.
- The entrant must provide the `/feedback` Codex Session ID from the primary thread where the majority of core functionality was built.

BOOTMUX mapping:

```text
Codex
  implementation engine
  → Go Companion
  → SwiftUI client
  → ESP32-S3 firmware
  → VM harness
  → tests and repair cycles

GPT-5.6
  architecture and verification engine
  → asymmetric input/output design
  → protocol and bounded-runtime contracts
  → adversarial lifecycle and overflow review
  → evidence and public-claim boundaries

Human
  product owner and final authority
  → selected the problem and hardware direction
  → performed physical setup and acceptance
  → accepted or rejected repairs
  → owns final narration, claims, and submission
```

### 2. Track

BOOTMUX should enter **Developer Tools**. The primary audience is developers and operators bootstrapping terminal and Codex access on a machine whose normal development or AI path is not ready.

A project may enter only one track.

### 3. Working-project requirement

The project must install and run consistently on its declared platform and must function as shown in the video and description.

BOOTMUX must therefore avoid claiming a general production product. Its submission claim is a bounded working path:

```text
physical input:
iPhone → BLE → ESP32-S3 → USB HID → target

independently observed return:
target PTY / Codex output → BOOTMUX Companion → WebSocket → iPhone
```

The physical input and observed output must not be represented as the same evidence source. Sent input must never be synthesized into fake terminal output.

### 4. Existing-project boundary

Pre-existing projects are allowed, but only work added during the Submission Period is evaluated. The repository must distinguish earlier concept work from Build Week implementation and preserve dated evidence such as commits, Codex sessions, artifacts, or public-safe receipts.

BOOTMUX records this boundary in:

- `docs/submission/BUILD_WEEK_SCOPE_LEDGER.md`
- repository commit history
- `docs/submission/CODEX_GPT56_EVIDENCE_LEDGER.md`
- physical and VM evidence documents

### 5. Submission package

A complete submission requires:

1. a working project built with Codex and GPT-5.6;
2. one selected track;
3. a text description explaining the project and how it works;
4. a public YouTube demonstration video under three minutes;
5. clear audio narration covering the project, Codex use, and GPT-5.6 use;
6. a repository URL for judging and testing;
7. a public repository with relevant licensing, or a private repository shared with the required judge addresses;
8. the `/feedback` Session ID from the Primary Build Thread;
9. English submission material or an English translation.

The video must not rely on unlicensed music, third-party trademarks, or copyrighted material without permission. Judges are not required to watch beyond three minutes.

### 6. Additional Developer Tools requirements

A Developer Tools submission must include:

- installation instructions;
- supported platforms;
- a way for judges to test without rebuilding from source.

BOOTMUX satisfies the no-rebuild direction with:

```text
Real Hardware Proof
  recorded iPhone → BLE → ESP32-S3 → USB HID demonstration

Judge Test Path
  standalone offline Judge Replay Mode
  packaged live local Judge Mode
  public-safe BOOTMUX_READY fixture
```

Judge Mode is a software review path and must not be presented as physical HID proof.

### 7. Testing and access

Judges may test the project, but they are not required to. The working project or test path must remain available free of charge through the judging period. Because BOOTMUX uses unusual hardware, the Sponsor may request physical access at its discretion.

### 8. Post-deadline changes

The submitted entry cannot be substantively changed after the Submission Period closes, except for narrow changes explicitly permitted by the Sponsor or Devpost.

## Judging criteria

After the baseline eligibility and theme check, projects are scored on four equally weighted criteria:

1. **Technological Implementation** — how thoroughly and skillfully Codex was used, and whether the implementation reflects genuine effort and works;
2. **Design** — whether it is a coherent runnable product experience rather than only a technical proof;
3. **Potential Impact** — whether it solves a credible, specific problem for a real audience;
4. **Quality of the Idea** — creativity, novelty, and differentiation from existing concepts.

The criteria are also used in that order for tie-breaking.

## What BOOTMUX must become for this competition

BOOTMUX is not required to become a complete remote-administration product. It is required to become the smallest credible, demonstrable **physical first mile for Codex**.

### Core competition claim

> **The physical first mile for Codex. Built by Codex. Architected and hardened with GPT-5.6.**

The submission should prove five things clearly:

### A. Real problem

There is a gap before SSH, remote tooling, a normal terminal workflow, or an on-device AI environment is ready. During bare-metal setup, recovery, clean-VM provisioning, or broken remote access, the user may have no practical way to ask AI for help or return terminal output to it.

### B. Real physical action

An iPhone sends committed text over BLE to an ESP32-S3, which appears to the target as a USB HID keyboard. This is not only a simulated WebSocket terminal.

### C. Independent observed return

The target-side Companion returns actual observed PTY or Codex output to the iPhone. BOOTMUX distinguishes input acknowledgement from independently observed output.

### D. Codex-centered result

Codex is both:

1. the implementation engine that built the major BOOTMUX layers; and
2. the target agent reached through the resulting path.

This creates the central Build Week narrative:

> Codex helped build the path that extends Codex itself into a machine before the normal AI workflow is ready.

### E. GPT-5.6-centered result

GPT-5.6 must be shown as a concrete architecture and verification collaborator, not a decorative model name. The strongest evidence is its role in:

- separating physical input from independently observed output;
- defining bounded queues, lifecycle rules, fail-closed behavior, and protocol limits;
- identifying BLE queue ownership hazards;
- reviewing VM transcript path binding and bounded Mirror behavior;
- maintaining the distinction between code-green, owner-observed, and still-unproven claims.

## BOOTMUX scoring strategy

```yaml
technological_implementation:
  show:
    - Codex-built Go, SwiftUI, firmware, VM, and test layers
    - physical BLE and USB HID path
    - real Codex invocation and BOOTMUX_READY return
    - bounded and fail-closed engineering

design:
  show:
    - one understandable end-to-end flow
    - clear iPhone controls and visible state
    - no-rebuild Judge Mode
    - honest separation of real hardware and replay

potential_impact:
  audience:
    - bare-metal setup
    - recovery shell users
    - headless-machine operators
    - clean VM and field provisioning workflows
  message: normal AI access can disappear exactly when it is most needed

quality_of_idea:
  differentiation:
    - not another LLM web form
    - not merely SSH
    - physical input plus independent observed return
    - Codex building its own physical first mile
```

## Current verified BOOTMUX state

```yaml
primary_codex_thread: CONFIRMED
feedback_receipt: CAPTURED_PRIVATELY
codex_majority_core_work: COMPLETE
meaningful_gpt_5_6_evidence: RECORDED_PUBLICLY
license: MIT_GREEN
judge_mode: GREEN
iphone_to_ble_to_usb_hid: BOUNDED_PHYSICAL_ASCII_PATH_OBSERVED
codex_installation_clean_arm64_vm: GREEN
bootmux_ready:
  direct_vm: PASS
  companion_codex_prompt: PASS
  physical_iphone_return: PASS
hid_mirror: CODE_GREEN_PHYSICAL_CONFIRMATION_PENDING
selectable_copy: PENDING_OWNER_CONFIRMATION
clear_visible_feedback: PENDING_OWNER_CONFIRMATION
repeatability: PENDING
registration: HUMAN_CONFIRMATION_PENDING
final_public_video: IN_PROGRESS
final_submission: NOT_CONFIRMED
production_ready: false
```

## Remaining blockers

```yaml
submission_blockers:
  - registration confirmation
  - final narrated video edit
  - privacy review
  - public YouTube upload and signed-out link check
  - final Devpost field review
  - final submission confirmation

high_value_physical_evidence:
  - selectable copy and exact paste
  - visible CLEAR acceptance
  - physical HID Mirror
  - repeatability receipt
```

The additional physical evidence improves judging strength, but must not be marked passed unless it is actually observed.

## Final source index

- [Official Rules](https://openai.devpost.com/rules)
- [Official FAQ](https://openai.devpost.com/details/faqs)
- [Hackathon overview](https://openai.devpost.com/)
- [Submissions-open update](https://openai.devpost.com/updates/45282-openai-build-week-submissions-are-open-plugin-launch)
- [Build Week guidance update](https://openai.devpost.com/updates/45362-openai-build-week-halfway-there-where-are-you)

## Change-control rule

Before final submission:

1. reopen the Official Rules and FAQ;
2. confirm the exact Devpost form fields and deadline;
3. verify every public link in a signed-out browser;
4. preserve the private `/feedback` Session ID outside the repository;
5. update this document only when the official sources or verified BOOTMUX state changes.
