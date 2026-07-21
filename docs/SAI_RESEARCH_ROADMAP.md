# SAI Research Roadmap

## Purpose and claim boundary

This roadmap develops SAI-originated BOOTMUX research hypotheses without changing the current Build Week product claim.

The implemented Build Week slice proves a bounded physical ASCII input path, an independently observed PTY/Codex return path, a clean ARM64 VM Codex installation, and no-build Judge Mode. It does **not** currently implement or prove a complete automated event classifier, policy gate, structured recovery executor, evidence verifier, recovery-capsule runtime, or autonomous repair system.

The named mechanisms below are research concepts unless a later document explicitly promotes them with runnable code, tests, and measured evidence. Definitions and attribution are maintained in [SAI Research Hypotheses](SAI_RESEARCH_HYPOTHESES.md).

## Status model

```text
CONCEPT
  ↓ complete definition and invariants
SPECIFIED
  ↓ executable contract and negative cases
PROTOTYPED
  ↓ runnable implementation
MEASURED
  ├── SUPPORTED
  ├── REVISE
  └── REJECTED
```

Code presence alone does not advance a hypothesis. A status change requires its declared evidence.

## Integration rules

A research feature may enter the core product only when:

- the shortest demonstrated BOOTMUX path remains available;
- deterministic fallback behavior exists;
- failure is explicit and fail-closed;
- sent input, replayed evidence, model inference, and observed machine output remain distinct;
- credentials and private infrastructure are excluded from model context and public artifacts;
- human approval and stop controls remain effective;
- benchmarks compare against a declared baseline;
- the Claim and Evidence Matrix is updated only after evidence exists.

## H0 — Measurement and replay foundation

Build public-safe synthetic fixtures, recorded bounded PTY streams, declared fault scenarios, transport counters, model-call counters, probe counts, replay tooling, and a benchmark schema.

**Promotion gate:** identical incidents can be replayed across raw and experimental paths with comparable correctness, byte, latency, and model-use measurements.

## H1 — TTYRETINA

Explore a terminal codec that emits sparse semantic events while retaining bounded raw fallback evidence on the target.

**Question:** can BOOTMUX reduce transport and model context without hiding terminal state required for diagnosis?

**Promotion gate:** measured fidelity against raw PTY baselines, explicit unknown-state behavior, and deterministic fallback.

## H2 — EPOCHROOT

Explore state-rooted epochs that transmit only deltas capable of advancing a verified recovery objective.

**Question:** can reconnect and replay cost fall while ordered intent and durable evidence remain safe?

**Promotion gate:** canonical versioned encoding, root-consistency checks, stale-replay tests, and byte/latency measurements.

## H3 — SYNDCOMP and SYNDROMUX

Explore bounded syndrome-style diagnostic probes and multiplexed evidence collection.

**Question:** can a smaller adaptive probe set isolate common failure classes without creating false certainty?

**Promotion gate:** declared diagnostic matrices, ambiguity detection, missing/stale/denied probe handling, and comparison with fixed sequential probes.

## H4 — VOIDCODE

Explore explicit abstention when available evidence cannot justify a recovery action.

**Question:** can uncertainty stop mutation rather than being converted into a plausible command?

**Promotion gate:** negative tests demonstrating that contradictory, incomplete, or out-of-scope evidence disables automatic mutation.

## H5 — CAUSALCLOCK and STRATAROOT

Explore causal invalidation of evidence and versioned layered state roots.

**Question:** can BOOTMUX reject evidence that is recent in time but invalid after a relevant machine transition?

**Promotion gate:** deterministic invalidation rules, schema migration tests, and stale-evidence rejection across reconnects.

## H6 — ROOTFIT

Explore compatibility scoring for reusing previously successful diagnostic or recovery programs.

**Question:** can historical work be reused without allowing past success to override failed current compatibility checks?

**Promotion gate:** explicit feature vectors, applicability rejection cases, and comparison against always-rerun and always-reuse baselines.

## H7 — Effect-bounded experiment cells

Explore constrained environments for testing proposed recovery operations while keeping modeled, counterfactual, observed, and externally committed effects distinct.

**Promotion gate:** registered effect adapters, unsupported-effect blocking, resource limits, teardown proof, and no promotion of simulated success into real success.

## H8 — Integrated sparse recovery

Combine only mechanisms that independently reached a supported measured state.

```text
bounded observation
→ sparse event or probe selection
→ explicit uncertainty state
→ deterministic policy evaluation
→ human approval where required
→ structured bounded execution
→ independent evidence
```

**Promotion gate:** end-to-end benchmarks must show a defensible improvement over the raw baseline without weakening correctness, evidence quality, stop behavior, or human authority.

## Research exclusions

This roadmap does not claim:

- implementation of the named mechanisms in the Build Week product;
- autonomous recovery safety;
- world-first status, patentability, optimality, or freedom to operate;
- benchmark superiority before measurements exist;
- replacement of the current bounded ASCII/HID and PTY return architecture.

The current product roadmap is [Roadmap](ROADMAP.md). Current implementation claims remain governed by [Claim and Evidence Matrix](submission/CLAIM_EVIDENCE_MATRIX.md).