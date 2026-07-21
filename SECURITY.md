# Security Policy

## Project maturity

BOOTMUX is an early-stage research and prototype project. It is not yet suitable for unattended administration of important or production computers.

## Security model

BOOTMUX separates reasoning, approval, execution, and verification.

```text
terminal observation
→ event classification
→ model proposal
→ deterministic policy evaluation
→ user approval when required
→ structured execution
→ machine evidence
→ verification
```

Model output, terminal content, transport input, diagnostic artifacts, and cached recovery programs are treated as untrusted until validated.

Research optimizations such as TTYRETINA, EPOCHROOT, SYNDROMUX, SYNDCOMP, VOIDCODE, CAUSALCLOCK, STRATAROOT, ROOTFIT, JANUSPROBE, and Counterfactual Effect Receipts must never weaken the policy boundary.

## Non-negotiable properties

- model output is never passed directly to a shell interpreter;
- mutation requires the declared approval class;
- the model cannot approve its own operation;
- the model cannot alter the policy gate or its evidence;
- credentials are not exposed to model context or terminal artifacts;
- destructive operations are denied by default;
- execution output is bounded and redacted before transport;
- transport retry cannot duplicate a committed mutation;
- stop and revocation remain available during congestion;
- insufficient or contradictory evidence produces abstention rather than forced repair;
- counterfactual evidence cannot satisfy a committed-success proof obligation;
- reused diagnostic artifacts require a current applicability check;
- stale evidence cannot authorize an action after declared causal invalidation.

## Approval classes

### Read-only probe

A bounded read operation may be eligible for automatic execution only when its executable, arguments, path scope, output limit, network effect, privilege behavior, and state-root assumptions are validated.

A Policy-Certified Probe Prefix certifies only these declared policy properties. It does not prove universal absence of side effects or operating-system defects.

### Mutation

File writes, package installation, service changes, permission changes, repository commits, and configuration changes require visible approval.

### Strong mutation

Reboot, firewall changes, SSH changes, user or group changes, authentication changes, and externally committed effects require stronger confirmation and additional evidence.

## Default restrictions

BOOTMUX must not automatically:

- initialize or repartition storage;
- perform unbounded recursive deletion;
- delete accounts;
- export passwords, tokens, cookies, or private keys;
- disable platform security;
- alter the policy gate;
- approve its own actions;
- escalate privileges without explicit approval;
- execute arbitrary downloaded code without verification and approval;
- assign silent fake success to an unsupported external effect;
- perform mutation after VOIDCODE abstention;
- promote counterfactual evidence to committed evidence;
- reuse a diagnostic program after its policy, capability, ABI, or root conditions no longer match.

## Effect-bounded experiments

An experiment cell may constrain local filesystem, process, and selected network effects. It must not claim universal side-effect freedom.

Every attempted effect must be:

- allowed and observed;
- denied and recorded;
- captured by a registered adapter;
- or treated as unsupported and blocked.

Evidence classes remain distinct:

```text
OBSERVED        directly observed machine evidence
COUNTERFACTUAL  isolated, modeled, or mocked result
COMMITTED       externally executed and confirmed effect
```

A real external effect requires new approval, an idempotence check, and a Committed Effect Receipt.

## Research safety rules

- TTYRETINA retains bounded raw fallback evidence on the target.
- SYNDCOMP refuses an underdetermined diagnostic matrix.
- SYNDROMUX reports missing, stale, denied, and contradictory probe outcomes explicitly.
- VOIDCODE disables automatic mutation after abstention.
- CAUSALCLOCK invalidation takes precedence over an unexpired time-based TTL.
- STRATAROOT schemas and canonical encodings are versioned.
- ROOTFIT historical success cannot override a failed current compatibility check.
- research components require deterministic fallbacks and disable switches before promotion into the core path.

## Credential handling

- Authentication remains user-controlled.
- Passwords and tokens must not be placed in model prompts.
- Companion must redact credential-like values before transmitting terminal context.
- Logs and evidence must record that authentication occurred without recording the secret.
- Public fixtures must use invalid placeholder values.

## Reporting vulnerabilities

Do not publish exploit details or sensitive environment data in a public issue.

Until a dedicated private disclosure channel is established, open a minimal public issue stating that a security report is available, without including reproduction details, secrets, affected infrastructure, or personal contact information. Project maintainers can then establish a private follow-up channel.

## Scope boundaries

The repository does not currently claim:

- production readiness;
- complete platform isolation;
- resistance to a hostile physical operator;
- secure boot or signed firmware update completion;
- universal terminal parsing;
- safe arbitrary shell execution;
- universal external-service simulation;
- world-first, optimality, patentability, or freedom-to-operate conclusions;
- validated performance or lightweight benchmark superiority.

These capabilities require implementation, threat modeling, testing, measurement, and review before any claim changes.

## Supported versions

No version is currently supported for security-critical use.
