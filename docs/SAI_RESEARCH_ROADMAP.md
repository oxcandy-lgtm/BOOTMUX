# SAI Research Roadmap

## Purpose

This roadmap matures the SAI-originated BOOTMUX research hypotheses without blocking the core R0–R7 product path.

The main implementation roadmap proves that BOOTMUX can connect, expose a verified terminal, apply a policy gate, and bootstrap target-side Codex. This research roadmap asks a different question:

> Can BOOTMUX reduce transport, model calls, repeated execution, and recovery uncertainty while preserving or improving evidence quality and safety?

The roadmap is evidence-gated, not date-gated. A hypothesis does not advance because code exists; it advances only when its declared evidence exists.

See [SAI Research Hypotheses](SAI_RESEARCH_HYPOTHESES.md) for definitions and attribution.

## Status model

```text
CONCEPT
  ↓ definition complete
SPECIFIED
  ↓ executable contract and tests exist
PROTOTYPED
  ↓ benchmark harness produces evidence
MEASURED
  ├── SUPPORTED
  ├── REVISE
  └── REJECTED
```

## Integration rule

Research work must not destabilize the shortest credible BOOTMUX demonstration.

```text
Core path first:
R1 transport
→ R2 iPhone surfaces
→ R3 verified PTY
→ R4 deterministic terminal events
→ R5 policy-gated recovery
→ R6 target-side Codex
→ R7 integrated demo

Research overlays:
H0 measurement
→ H1 TTYRETINA
→ H2 EPOCHROOT
→ H3 SYNDCOMP and SYNDROMUX
→ H4 VOIDCODE
→ H5 CAUSALCLOCK and STRATAROOT
→ H6 ROOTFIT
→ H7 bounded experiment cells
→ H8 integrated sparse recovery
```

A research feature may be used in the primary demo only when it has a deterministic fallback.

---

# H0 — Measurement and replay foundation

## Goal

Create a repeatable harness that can compare raw, compressed, semantic, cached, and compiled recovery paths against identical synthetic incidents.

## Deliverables

- synthetic, public-safe terminal fixtures;
- recorded PTY byte streams containing ANSI control behavior;
- declared fault scenarios with expected evidence;
- transport byte and packet counters;
- model-call and token counters;
- probe count and round-trip counters;
- deterministic replay runner;
- baseline fixed diagnostic sequences;
- benchmark result schema;
- public-safety scanner for fixtures and evidence.

## Required baselines

1. raw PTY forwarding;
2. conventional byte compression;
3. fixed deterministic probe tree;
4. sequential cloud-generated probes;
5. cached probe tree without root matching.

## Acceptance gate

- the same fixture produces the same canonical result on repeated replay;
- every byte sent between logical components is counted;
- every model call and probe execution is counted;
- no benchmark uses private logs, credentials, hostnames, addresses, or device IDs;
- raw and semantic paths can be compared from the same input;
- failure classification and proof completion are scored independently.

## Stop condition

Do not claim any lightweight advantage before H0 is complete.

---

# H1 — TTYRETINA semantic terminal codec

## Goal

Convert terminal behavior into sparse semantic events while retaining bounded raw evidence for fallback.

## Deliverables

- VT/ANSI state machine;
- bounded target-side raw ring buffer;
- command-start and process-exit events;
- stdout and stderr novelty detection;
- repeated-line and progress folding;
- prompt and current-directory events where reliably observable;
- fidelity levels F0–F3;
- parser-confidence and unsupported-sequence handling;
- raw-excerpt retrieval by event and byte range.

## Acceptance gate

- fixture output is reconstructed sufficiently for the declared semantic claims;
- ANSI cursor movement and carriage-return progress do not create false new lines;
- exit status is never inferred only from visible text;
- unknown or unsupported terminal behavior triggers fidelity escalation;
- controlled known failures use at least 80% fewer outbound bytes than raw PTY forwarding;
- raw evidence remains locally retrievable for every transmitted semantic event within the retention window.

## Rejection signals

- metadata exceeds raw traffic for representative fixtures;
- semantic events hide information required to identify controlled failures;
- the codec produces false success or false process completion.

---

# H2 — EPOCHROOT sparse transport

## Goal

Separate delivery semantics and synchronize through versioned hierarchical evidence roots.

## Deliverables

- Reflex, Intent, Evidence, and Telemetry planes;
- adaptive epoch framing;
- canonical CBOR or equivalent compact encoding;
- sequence, deduplication, and idempotence fields;
- stop and revocation priority;
- root schema identifiers;
- reconnect handshake;
- partial-state resynchronization;
- raw fallback independent of semantic compression.

## Acceptance gate

- stale pointer motion may be dropped without dropping text or approval intent;
- stop preempts lower-priority traffic under congestion;
- an Evidence item is not lost after acknowledged persistence;
- reconnect does not replay a committed mutation;
- reconnect transfers less data than full transcript replay for long sessions;
- protocol metadata cost is reported separately from payload reduction;
- malformed or unknown epoch schemas fail closed.

## Research comparison

Compare:

```text
single reliable stream
vs
semantic planes without epochs
vs
EPOCHROOT planes and roots
```

---

# H3 — SYNDCOMP and SYNDROMUX known-fault prototype

## Goal

Compile a bounded incident into a compact diagnostic probe program and transmit a rateless syndrome instead of performing sequential cloud diagnosis.

## Initial fault set

- permission failure;
- disk threshold failure;
- DNS failure;
- executable missing;
- package-manager lock;
- service inactive.

## Deliverables

- Fault Hypothesis IR;
- versioned Probe IR;
- hypothesis-to-outcome matrix;
- deterministic compiler for the initial set;
- rateless probe ordering;
- syndrome encoder and decoder;
- redundant-probe option;
- expected information-value estimator;
- Proof Frontier mapping;
- Policy-Certified Probe Prefix verifier;
- structured Evidence Receipt output.

GPT-5.6 may propose hypotheses, but the compiler, policy checks, and decoder must remain deterministic and testable.

## Acceptance gate

- every initial fault is distinguishable in the declared test matrix;
- the compiler refuses an underdetermined matrix rather than inventing separation;
- one missing or intentionally corrupted probe is detected in the redundancy test;
- known incidents require fewer cloud round trips than sequential cloud diagnosis;
- syndrome bytes, compiler metadata, and raw fallback bytes are reported separately;
- mutation opcodes never appear in an automatically certified probe prefix;
- success remains tied to Evidence Receipts rather than decoder confidence alone.

## Rejection signals

- a fixed probe tree performs equally well with materially lower complexity;
- compiler overhead exceeds the savings for the target incident set;
- matrix assumptions cannot be kept synchronized with real probe semantics.

---

# H4 — VOIDCODE and open-world abstention

## Goal

Prevent unknown or contradictory incidents from being forced into known repair classes.

## Deliverables

- explicit `unknown` hypothesis;
- reserved reject regions;
- best-to-second-best separation margin;
- mandatory anchor probes;
- stale and denied result handling;
- unexplained-observation accounting;
- F2 and F3 fidelity escalation;
- mutation lock after abstention;
- synthetic out-of-distribution incident set.

## Acceptance gate

- no declared unknown fixture is automatically assigned a mutation-capable known class;
- contradictory anchor probes force abstention;
- missing evidence cannot silently become `PASS`;
- abstention displays the evidence still required;
- known-fault accuracy and unknown detection are both reported;
- threshold selection is calibrated on a separate fixture set from evaluation.

## Core metric

```text
forced-known-error rate on unknown incidents = 0
```

This is a safety target. If it cannot be reached for a declared scope, automatic mutation for that scope remains disabled.

---

# H5 — CAUSALCLOCK and STRATAROOT

## Goal

Make evidence validity and synchronization depend on causal state change rather than fixed time alone.

## Deliverables

- evidence dependency schema;
- mutation invalidation declarations;
- preserved-evidence declarations;
- Identity, Capability, Policy, Execution, and Volatile roots;
- canonical root serialization;
- component-root update events;
- time-based fallback decay;
- stale-evidence detector;
- root mismatch diagnostics.

## Acceptance gate

- a package installation invalidates executable inventory and disk evidence but not architecture identity;
- a network route change updates the Volatile root without invalidating stable identity;
- a policy change invalidates active diagnostic reuse contracts;
- evidence is rejected after a declared causal invalidation even when its TTL has not expired;
- stable evidence is not repeatedly refreshed only because volatile state changed;
- monolithic-root and STRATAROOT resynchronization costs are compared.

## Rejection signals

- dependency declarations become too broad to produce useful savings;
- invalidation bugs allow stale evidence to authorize actions;
- maintaining roots costs more than full state refresh for the target scope.

---

# H6 — ROOTFIT proof-carrying reuse

## Goal

Reuse prior SYNDCOMP artifacts only when their applicability conditions match current roots, policy, capabilities, and opcode semantics.

## Deliverables

- compiled artifact manifest;
- exact, compatible, partial, and no-fit outcomes;
- policy-root and ABI guards;
- opcode semantic versioning;
- historical outcome statistics;
- artifact invalidation events;
- partial recompilation path;
- built-in probe pack fallback;
- optional local template ranker with no execution authority.

## Acceptance gate

- exact-fit reuse produces the same probe program as a fresh compile for the fixture;
- policy changes make affected artifacts ineligible;
- artifacts from an incompatible operating-system family are rejected;
- partial fit executes no unchecked suffix;
- reused artifacts reduce cloud model calls on repeated incidents;
- historical success never overrides a failed current applicability check;
- every reuse decision produces a machine-readable match explanation.

## Primary claim tested

> Previously proven diagnostic reasoning can be reused safely when the proof of applicability is cheaper than repeating the reasoning.

---

# H7 — Effect-Bounded Experiment Cell and Counterfactual Receipts

## Goal

Test selected reversible repair hypotheses without confusing isolated simulation with committed external effects.

## Scope rule

This phase begins with local filesystem and process effects only. External network and service adapters are added individually and remain deny-by-default.

## Deliverables

- operating-system-independent effect interface;
- disposable local workspace;
- local filesystem effect manifest;
- network deny-by-default mode;
- process and attempted-effect observation;
- typed Effect Intent;
- `OBSERVED`, `COUNTERFACTUAL`, and `COMMITTED` receipt classes;
- unsupported-effect fail-closed path;
- approval boundary for committing external effects;
- Linux adapter research using available isolation mechanisms;
- JANUSPROBE contract for selected reversible failures.

## Acceptance gate

- an isolated file mutation is discarded after the experiment;
- a denied network attempt is recorded without leaving the declared cell;
- an unsupported protocol does not receive silent fake success;
- a Counterfactual Receipt can never satisfy a production-success proof obligation;
- committing a captured effect requires a new approval and idempotence check;
- test fixtures demonstrate rollback and blocked escape attempts;
- documentation never claims universal side-effect freedom.

## Rejection signals

- relevant effects cannot be bounded for the target scenario;
- a protocol-aware mock creates more false confidence than diagnostic value;
- the isolation mechanism makes the core demo platform-specific without a fallback.

---

# H8 — Integrated sparse recovery experiment

## Goal

Run one controlled incident through the complete SAI research path and compare it with all H0 baselines.

## Required sequence

1. replay a controlled terminal incident;
2. produce TTYRETINA events;
3. establish current Proof Frontier and STRATAROOT state;
4. attempt ROOTFIT reuse;
5. compile with SYNDCOMP if no safe fit exists;
6. execute the Policy-Certified Probe Prefix;
7. transmit a rateless SYNDROMUX syndrome;
8. accept a known class or enter VOIDCODE abstention;
9. update evidence through CAUSALCLOCK;
10. produce an Epoch-Sealed Evidence Receipt;
11. reconnect and resume without full transcript replay;
12. report bytes, latency, probes, model calls, safety outcomes, and proof completion.

## Acceptance gate

- every component can be disabled independently for ablation testing;
- the run is reproducible from public synthetic fixtures;
- results include raw measurements, not only percentages;
- no counterfactual result is reported as committed evidence;
- no unknown fixture is forced into an automatic repair;
- no unapproved mutation occurs;
- comparison includes implementation complexity and metadata overhead;
- unsupported hypotheses are marked `REVISE` or `REJECTED` rather than hidden.

---

# Research-to-product promotion rules

A research component can enter the core R roadmap only when:

- it has deterministic fallback behavior;
- its public protocol and state schemas are versioned;
- its safety invariants have negative tests;
- it improves a declared metric or safety property;
- its complexity and failure modes are documented;
- it does not require private data for ordinary operation;
- it does not make the primary demonstration less repeatable;
- it has an explicit disable switch.

Recommended promotion mapping:

| Research phase | Earliest core integration |
|---|---|
| H0 | R3 |
| H1 | R4 |
| H2 | R3–R4 after base transport stability |
| H3 | R5 |
| H4 | R5 before automatic mutation |
| H5 | R5–R6 |
| H6 | after repeated incident evidence exists |
| H7 | stretch track until isolation evidence is strong |
| H8 | after R7 remains reproducible without research features |

# Immediate implementation order

The shortest research vertical slice is:

```text
synthetic PTY fixture
→ deterministic TTYRETINA event
→ fixed two-fault hypothesis matrix
→ three read-only probes
→ compact syndrome
→ Evidence Receipt
→ byte and round-trip comparison
```

Do not begin with:

- neural log parsing;
- arbitrary shell generation;
- automatic mutation;
- external API mocking;
- a large local language model;
- universal operating-system support;
- claims of optimality or novelty without measurement and review.

# Final gate

The SAI research program succeeds only if BOOTMUX becomes measurably lighter or safer under a declared scope.

> A name, diagram, or sophisticated mechanism is not evidence. The benchmark and the receipt decide.
