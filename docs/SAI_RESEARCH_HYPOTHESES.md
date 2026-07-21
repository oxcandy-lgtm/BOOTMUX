# SAI Research Hypotheses for BOOTMUX

## Origin and attribution

The named research hypotheses and BOOTMUX-specific synthesis in this document were proposed by **SAI (宰)** during the architecture development of BOOTMUX.

> **SAI-originated research direction:** convert machine uncertainty into the smallest safe set of proof-bearing observations and executions required to advance recovery.

This attribution applies to the BOOTMUX-specific names, composition, execution contracts, and research formulations described below. It does **not** claim invention of every underlying foundation. Syndrome-based diagnosis, error-correcting codes, group testing, semantic communication, event-driven parsing, capability security, proof-carrying systems, sandboxing, state synchronization, and information-gain probe selection all have prior research and implementations.

The research claim is narrower:

> BOOTMUX explores a runtime-generated, proof-indexed, safety-constrained diagnostic and recovery architecture that combines these foundations for low-bandwidth out-of-band AI bootstrap and repair.

These are research hypotheses, not completed product claims, patent opinions, or assertions of world-first status.

## Research status legend

| Status | Meaning |
|---|---|
| `CONCEPT` | Named hypothesis with an architectural definition |
| `SPECIFIED` | Inputs, outputs, invariants, and failure behavior are documented |
| `PROTOTYPED` | A runnable implementation exists |
| `MEASURED` | Benchmarks exist against a declared baseline |
| `SUPPORTED` | Evidence supports the hypothesis within the tested scope |
| `REVISE` | Evidence identifies a useful direction but the hypothesis or mechanism must change |
| `REJECTED` | Results do not support the hypothesis or costs exceed benefits |

All hypotheses in this document begin as `CONCEPT` unless explicitly updated by measured evidence.

---

# 1. EPOCHROOT Sparse Runtime

**Status:** `CONCEPT`

## Definition

EPOCHROOT is a state-rooted sparse transport and execution architecture that carries only the semantic deltas required to advance a machine's verified recovery proof frontier.

```text
human input
terminal events
AI proposals
policy decisions
evidence receipts
        ↓
short adaptive epochs
        ↓
state-rooted semantic deltas
        ↓
minimal verified execution
```

EPOCHROOT is not merely compression. Its goal is to avoid producing, transmitting, or re-executing information that cannot advance the current recovery objective.

## Transport planes

| Plane | Content | Delivery behavior |
|---|---|---|
| Reflex | pointer and scroll motion | newest useful state wins; stale motion may be discarded |
| Intent | text, commands, approvals, stop | ordered and deduplicated |
| Evidence | exit state, proof claims, roots, receipts | durable and replay-safe |
| Telemetry | terminal progress and diagnostic context | semantic-first with raw fallback |

## Hypothesis

A transport that separates delivery semantics by operational meaning and synchronizes through verified state roots can reduce bytes, stale replay, and reconnect cost without weakening safety evidence.

## Required invariants

- stop and revocation outrank all non-safety traffic;
- text and approvals are never treated as disposable motion;
- evidence is not acknowledged only because a UI rendered it;
- reconnect cannot replay a mutation intent without idempotence checks;
- raw evidence remains available locally for bounded fallback;
- a state root identifies a declared schema and canonical serialization.

---

# 2. TTYRETINA

**Expanded name:** Event-Retinal Terminal Codec  
**Status:** `CONCEPT`

## Definition

TTYRETINA converts a raw PTY byte stream into sparse semantic terminal events while preserving a bounded raw ring buffer on the target for escalation and audit.

```text
raw PTY bytes
├── bounded raw ring buffer
└── VT/ANSI state machine
        ↓
logical screen and stream changes
        ↓
semantic terminal events
```

Example output:

```yaml
event:
  type: process_exited
  command_class: package_install
  exit_code: 13
  failure_skill: permission_error
  repeated_lines: 18
  novel_lines: 2
  raw_excerpt_available: true
```

## Fidelity ladder

```text
F0  state or failure signal
F1  semantic event
F2  relevant bounded excerpt
F3  bounded raw PTY segment
```

The codec escalates fidelity when parsing confidence is low, an unknown event appears, proof does not match prediction, or a user explicitly requests raw context.

## Hypothesis

For known terminal behaviors, semantic events can replace most repeated PTY traffic while preserving enough evidence to classify failures and request precise raw excerpts only when necessary.

## Non-goals

- TTYRETINA does not discard all raw logs.
- It does not treat a terminal as simple newline-delimited text.
- It does not rely on a neural model for deterministic ANSI and exit-state parsing.
- An optional sequence model may be researched only as a novelty sentinel, never as the authority for execution.

---

# 3. Proof Frontier Execution

**Status:** `CONCEPT`

## Definition

A Proof Frontier is the boundary between claims already supported by machine evidence and claims still required to complete an objective.

```text
Objective: install and launch target-side Codex

PROVEN   supported operating system
PROVEN   supported architecture
PROVEN   network route available
MISSING  installer completed
MISSING  executable discovered
MISSING  version returned
MISSING  initial launch succeeded
```

Execution planning asks:

> What is the smallest safe observation or action that can advance one missing proof obligation?

It does not ask only:

> What command would normally be run next?

## Hypothesis

Representing recovery as proof obligations can reduce repeated diagnostics, make success criteria explicit, and prevent AI-generated declarations from being mistaken for machine-confirmed completion.

---

# 4. Evidence-Indexed Semantic Multiplexing

**Status:** `CONCEPT`

## Definition

Evidence-Indexed Semantic Multiplexing schedules transport according to the missing evidence required by the current Proof Frontier.

A candidate item's conceptual priority is:

```text
priority ≈
  safety weight
  × expected proof relevance
  × novelty
  × expiry risk
  ÷ byte cost
```

This is not a fixed production formula. It defines the variables that an implementation must expose and measure.

## Example

If the objective requires proof that a binary was installed, the following evidence outranks repeated progress logs:

```text
executable path
version output
launch exit status
```

## Hypothesis

Scheduling by expected recovery-proof contribution per transmitted byte can outperform channel-only or byte-only priority rules under constrained BLE transport.

---

# 5. SYNDROMUX Recovery

**Expanded name:** Syndrome-Coded Diagnostic Multiplexing  
**Status:** `CONCEPT`

## Definition

SYNDROMUX represents the results of a selected diagnostic probe program as a compact syndrome that distinguishes competing fault hypotheses.

```text
fault hypotheses
├── permission failure
├── disk exhaustion
├── name-resolution failure
└── missing executable

selected probes
├── bounded writeability check
├── disk threshold check
├── resolver check
├── executable lookup
└── optional redundancy probe

observed probe results
        ↓
compact diagnostic syndrome
```

SYNDROMUX does not claim that syndrome diagnosis itself is new. Its research target is a BOOTMUX runtime in which syndrome bits are generated, prioritized, transmitted, decoded, and bound to proof obligations under explicit safety and bandwidth constraints.

## Rateless Proof Syndrome

The syndrome begins with the cheapest useful probes. Additional parity or disambiguation probes are added only while the result remains ambiguous.

```text
initial probes → ambiguous
additional probe → still ambiguous
additional parity probe → accepted or abstained
```

## Expected value scheduling

A probe candidate should consider:

```text
expected information gain
+ expected proof-frontier gain
+ unknown-detection value
- BLE byte cost
- latency
- execution risk
- approval cost
- evidence staleness risk
```

The true fault is unknown at selection time. Therefore the scheduler must use expected information gain over possible outcomes rather than a distance to an unavailable known truth.

## Hypothesis

A rateless diagnostic syndrome can identify common failures with fewer round trips and fewer transmitted bytes than sequential model-generated shell diagnosis, while redundant probes can detect or tolerate bounded observation errors.

---

# 6. SYNDCOMP

**Expanded name:** Runtime Syndrome Compiler  
**Status:** `CONCEPT`

## Definition

SYNDCOMP compiles a live machine incident into a temporary, rateless, error-correcting diagnostic program.

```text
GPT-5.6 or deterministic hypothesis source
        ↓
Fault Hypothesis IR
        ↓
SYNDCOMP
├── probe selection
├── probe ordering
├── expected-result matrix
├── redundancy and reject regions
├── decoder
└── policy requirements
        ↓
CapsuleVM probe program
```

## Inputs

```yaml
incident:
  state_roots: declared
  proof_frontier: declared

hypotheses:
  - permission_error
  - disk_full
  - dns_failure
  - executable_missing
  - unknown

available_probes:
  - id: inspect_writeability
    risk: read_only
    estimated_bytes: 3
    estimated_latency_ms: 5

constraints:
  max_bytes: 64
  max_latency_ms: 300
  privilege_escalation: forbidden
```

## Outputs

- a versioned probe bytecode program;
- a hypothesis-to-outcome matrix;
- an explicit unknown/reject region;
- required policy certificates;
- a decoder with acceptance margins;
- a raw-fidelity escalation rule;
- a declared proof obligation advanced by each accepted outcome.

## Hypothesis

Runtime compilation can create a smaller and more discriminating probe program than a universal static diagnostic sequence because it can use the current machine state, available capabilities, active policy, and missing proof obligations.

---

# 7. VOIDCODE

**Expanded name:** Reserved Unknown Space for Runtime Diagnostic Codes  
**Status:** `CONCEPT`

## Definition

VOIDCODE reserves regions of the diagnostic outcome space for explicit abstention instead of assigning every possible result to the nearest known failure.

A known class is accepted only when:

```text
distance to best codeword is within its correction radius
AND separation from the second-best class exceeds a margin
AND mandatory anchor probes match
AND required observations are not stale
AND unexplained observations remain below policy limits
```

Otherwise:

```yaml
decode:
  class: unknown
  decision: abstain
  mutation_allowed: false
  next_fidelity: F2_or_F3
```

## Hypothesis

Reserved reject regions and evidence-consistency gates can reduce dangerous forced classification of out-of-distribution incidents, at the cost of deliberate abstention and additional diagnostic traffic.

## Safety principle

> BOOTMUX must be able to say "insufficient evidence" before it is allowed to say "repair this."

---

# 8. Policy-Certified Probe Prefix

**Status:** `CONCEPT`

## Definition

A verifier identifies the longest prefix of a proposed probe program that satisfies the current BOOTMUX policy and state-root constraints.

A certificate may establish only declared properties such as:

```yaml
certificate:
  opcode_class: probe
  shell_interpolation: false
  bounded_output: true
  approved_path_scope: true
  network_effect: none
  privilege_change: none
  state_root_match: true
```

It does not prove that an operating system has no bugs or that every command is universally free of side effects.

## Hypothesis

Mechanically executing the longest policy-compliant read-only prefix can reduce cloud round trips and idle time while preserving the approval boundary for mutation and external effects.

---

# 9. CAUSALCLOCK

**Expanded name:** Mutation-Indexed Evidence Validity  
**Status:** `CONCEPT`

## Definition

CAUSALCLOCK determines evidence validity from causal invalidation events and dependency versions, with time-based decay only as a fallback.

```yaml
evidence:
  claim: disk_free_space_above_threshold
  depends_on:
    - filesystem_generation

  invalidated_by:
    - package_install
    - archive_extract
    - large_file_write
    - mount_change

  fallback_max_age_ms: 30000
```

A mutation declares what it invalidates and what it preserves.

```yaml
mutation:
  op: install_package

  invalidates:
    - executable_inventory
    - package_database
    - disk_free_space
    - affected_service_state

  preserves:
    - os_identity
    - cpu_architecture
```

## Hypothesis

Causal invalidation can avoid both unnecessary polling and unsafe reuse of stale evidence better than fixed TTLs alone.

---

# 10. STRATAROOT

**Expanded name:** Hierarchical Evidence Roots by Volatility  
**Status:** `CONCEPT`

## Definition

STRATAROOT separates machine state into roots with different volatility and trust requirements.

```yaml
state_roots:
  identity_root:
    - os_family
    - architecture
    - machine_class

  capability_root:
    - companion_version
    - supported_opcodes
    - target_agent_presence

  policy_root:
    - approval_rules
    - denied_operations
    - active_leases

  execution_root:
    - current_action
    - completed_receipts
    - proof_frontier

  volatile_root:
    - network_route
    - disk_space
    - active_user
    - service_state
```

An epoch root may commit the component roots without forcing every stable claim to be revalidated when only volatile state changes.

## Hypothesis

Hierarchical roots can reduce resynchronization and invalidation fan-out compared with a single monolithic machine-state root.

---

# 11. ROOTFIT

**Expanded name:** Proof-Carrying Diagnostic Reuse  
**Status:** `CONCEPT`

## Definition

ROOTFIT reuses a previously compiled diagnostic artifact only when its applicability contract matches the current machine and policy roots.

```yaml
compiled_probe_program:
  id: permission-cache-v3

  applicable_when:
    os_family:
      - linux
    companion_abi: 2
    required_opcodes:
      - inspect_owner
      - inspect_mode
      - inspect_current_user

    roots:
      identity_root: exact
      policy_root: exact
      capability_root: compatible
      volatile_root: ignored_or_refreshed

  invalidated_by:
    - parser_schema_change
    - policy_change
    - opcode_semantics_change
```

Matching results:

```text
exact fit   → reuse
partial fit → refresh missing assumptions or recompile a suffix
no fit      → GPT-5.6 or deterministic JIT compilation
```

## Hypothesis

Proof-carrying reuse of compiled diagnostic programs can eliminate repeated model inference for recurring incidents without treating historical success as universal validity.

## Principle

> The lightest inference is a previously proven inference that does not need to run again.

---

# 12. Effect-Bounded Experiment Cell

**Status:** `CONCEPT`

## Definition

An Effect-Bounded Experiment Cell constrains and records the effects of a diagnostic or repair experiment. It does not claim universal side-effect freedom.

The core interface is operating-system independent:

```text
deny undeclared external effects
capture attempted effect intents
use disposable local state where available
observe process and network behavior
produce typed effect receipts
fail closed for unsupported effects
```

A Linux adapter may combine:

- a disposable filesystem layer;
- Landlock restrictions;
- namespaces;
- seccomp filtering or mediation;
- eBPF observation, denial, or redirection;
- protocol-aware user-space proxies.

No individual mechanism is sufficient to simulate arbitrary external services.

---

# 13. Counterfactual Effect Receipt

**Status:** `CONCEPT`

## Definition

A Counterfactual Effect Receipt records an external effect that a program attempted inside an Effect-Bounded Experiment Cell without claiming that the external production effect occurred.

```yaml
effect_intent:
  kind: http_request
  destination_class: external_service
  operation: create_resource
  idempotency_supported: true

execution:
  externally_committed: false
  adapter: registered_mock

counterfactual_result:
  predicted_status: success
  confidence_class: bounded

proof_class:
  counterfactual: true
  production_success: false
```

Evidence classes remain distinct:

```text
OBSERVED        machine state directly observed
COUNTERFACTUAL  result produced in an isolated or modeled environment
COMMITTED       external effect actually executed and confirmed
```

Unsupported external effects are blocked rather than silently given fake success.

## Hypothesis

Typed separation of counterfactual and committed effects can let JANUSPROBE test selected repair hypotheses without confusing simulation evidence with production evidence.

---

# 14. JANUSPROBE, refined

**Status:** `CONCEPT`

## Definition

JANUSPROBE is a bounded experiment in which one reversible or effect-contained action serves two roles:

1. test a causal failure hypothesis;
2. test a potential repair outcome.

```yaml
janus_probe:
  hypothesis: cache_writeability_caused_failure

  temporary_action:
    create_isolated_writable_cache: true

  acceptance:
    - original_failure_disappears
    - expected output appears
    - no new failure class appears

  commit:
    automatic: false

  rollback:
    isolated_state_discarded: true
```

JANUSPROBE is prohibited when BOOTMUX cannot bound or capture the relevant external effects.

## Hypothesis

For selected reversible failure classes, a dual-purpose experiment can reduce the separate diagnose-then-repair cycle while preserving a clear distinction between temporary evidence and committed change.

---

# 15. Integrated SAI research architecture

```text
Raw PTY
  ↓
TTYRETINA
  ├── bounded raw ring buffer
  └── semantic terminal events
          ↓
Proof Frontier
          ↓
ROOTFIT
  ├── reusable proven diagnostic artifact
  └── no safe fit
          ↓
SYNDCOMP
  ├── runtime probe program
  ├── rateless syndrome plan
  ├── VOIDCODE reject regions
  └── policy requirements
          ↓
Policy-Certified Probe Prefix
          ↓
CapsuleVM
          ↓
SYNDROMUX
  ├── expected information value
  ├── proof-frontier value
  ├── byte and latency cost
  └── unknown-detection value
          ↓
Evidence Receipt
          ↓
CAUSALCLOCK
          ↓
STRATAROOT
          ↓
EPOCHROOT
```

For a reversible experiment branch:

```text
candidate hypothesis
  ↓
Effect-Bounded Experiment Cell
  ↓
JANUSPROBE
  ↓
Counterfactual Effect Receipt
  ↓
explicit approval when a real effect is required
  ↓
Committed Effect Receipt
```

---

# 16. Research evaluation plan

## Baselines

Every optimization must be compared against declared baselines:

1. raw PTY forwarding;
2. compressed raw forwarding;
3. deterministic fixed diagnostic sequence;
4. sequential LLM-generated probes;
5. cached fixed probe trees;
6. SYNDCOMP and SYNDROMUX variants.

## Primary metrics

### Transport

- bytes from target to phone;
- bytes from phone to target;
- BLE packets and retransmissions;
- p50, p95, and p99 operator latency;
- reconnect bytes and recovery time.

### Model use

- model calls per incident;
- input and output tokens;
- time waiting for cloud reasoning;
- fraction handled by ROOTFIT or built-in programs.

### Diagnosis

- correct known-fault classification;
- false known-fault classification;
- VOIDCODE abstention rate;
- unknown-fault detection rate;
- probes and round trips per incident;
- tolerance to one missing or incorrect probe result.

### Safety

- unapproved mutations;
- effects that escaped an experiment cell;
- counterfactual evidence misclassified as committed;
- stale evidence reused after causal invalidation;
- duplicate mutation after reconnect.

### Recovery proof

- proof obligations completed;
- false success declarations;
- amount of evidence required per completed objective;
- ability to resume from a verified frontier.

## Initial research targets

These are targets, not current achievements.

```yaml
targets:
  known_failure_semantic_byte_reduction_vs_raw: ">= 80%"
  repeated_progress_reduction: ">= 95%"
  known_failure_cloud_round_trips: "<= 2"
  unapproved_mutations: 0
  duplicate_committed_mutations: 0
  false_success_classifications: 0
  unknown_incident_forced_into_known_class: 0
  reconnect_requires_full_transcript: false
```

## Falsification criteria

A hypothesis must be revised or rejected when measured results show that:

- its metadata costs more than the bytes it saves;
- diagnosis latency exceeds the baseline without safety benefit;
- its abstention rate prevents useful recovery;
- it increases false confidence or false success;
- root maintenance causes excessive invalidation or synchronization;
- a simpler deterministic implementation performs equally well;
- the mechanism cannot be implemented within the target platform constraints.

---

# 17. Public claims policy

Allowed language:

- "proposed by SAI for BOOTMUX";
- "research hypothesis";
- "experimental architecture";
- "BOOTMUX-specific synthesis";
- "not yet validated";
- "inspired by established work in adjacent fields."

Language requiring strong evidence and external review:

- "world first";
- "provably optimal";
- "side-effect free";
- "mathematically safe" without a precisely scoped property;
- "patented" or "patentable";
- "production proven";
- benchmark superiority without reproducible data.

## Final SAI thesis

> **BOOTMUX should not send everything a machine says or execute everything an AI suggests. It should identify the smallest safe observation that can reduce uncertainty, advance a recovery proof, or justify an explicit abstention.**
