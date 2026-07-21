# Security Policy

## Project maturity

BOOTMUX is an early-stage research and prototype project. It is not suitable for unattended administration of important or production computers.

## Current implementation boundary

The Build Week slice is a user-operated physical-input and terminal prototype. It implements bounded BLE/HID framing, a bounded PTY/WebSocket Companion, a bounded one-shot Codex adapter, explicit transport separation, and public-safe evidence handling.

It does **not** currently implement the full autonomous recovery architecture described in the research documents. In particular, the current repository does not claim a complete:

- model proposal router;
- deterministic policy engine;
- structured mutation executor;
- approval-class enforcement system;
- evidence verifier for arbitrary recovery actions;
- sandbox for untrusted model-generated operations;
- secure unattended administration service.

The policy and proof rules below are requirements for any future autonomous layer, not claims that those controls are already enforced by the Build Week prototype.

## Current prototype safeguards

- the Companion binds to loopback by default;
- non-loopback binding requires the explicit `-allow-remote` flag;
- browser origins must match the request host, while native origin-less clients are allowed;
- WebSocket messages, JSON, terminal input, terminal output, queues, Codex prompts, Codex output, and execution time are bounded;
- overflow fails closed instead of silently truncating a claimed result;
- sent BLE/HID input is never synthesized into observed PTY or Codex output;
- BLE frames are session- and sequence-scoped;
- duplicate operations are acknowledged without being applied again;
- STOP, disconnect, parser failure, and terminal shutdown return input state toward neutral;
- authentication remains human-controlled;
- credentials, private endpoints, signing material, device identifiers, and the real `/feedback` Session ID are excluded from public evidence.

These safeguards do not make the prototype safe for hostile networks, hostile physical operators, or production use.

## Operator responsibilities

- use only a trusted local network for non-loopback Companion access;
- do not expose the Companion directly to the public internet;
- inspect commands before sending them through HID or the terminal;
- keep authentication secrets out of prompts, logs, screenshots, recordings, fixtures, and commits;
- verify the focused target before sending physical keyboard input;
- stop the demo if the target state, keyboard focus, network route, or evidence source is uncertain;
- treat terminal content and model output as untrusted data;
- retain human authority over authentication, mutation, and physical acceptance.

## Future autonomous recovery requirements

Any future model-directed recovery path must separate:

```text
observation
→ model proposal
→ deterministic policy evaluation
→ visible approval when required
→ structured execution
→ machine evidence
→ independent verification
```

Before such a path can be claimed, it must enforce at least these properties:

- model output is not passed directly to a shell interpreter as an autonomous action;
- the model cannot approve its own operation or alter the policy gate;
- mutations use typed tools with bounded arguments and path scope;
- destructive operations are denied by default;
- privilege, authentication, network, firewall, user, and reboot changes require stronger approval;
- retry cannot duplicate a committed mutation;
- stale, contradictory, or insufficient evidence causes abstention;
- counterfactual, mocked, replayed, and observed evidence remain distinct;
- externally committed effects require fresh approval, idempotence checks, and committed evidence;
- stop and revocation remain available during congestion or partial failure.

## Credential handling

- passwords, API keys, tokens, cookies, private keys, and authentication URLs must not be committed;
- authentication remains user-controlled;
- public fixtures must use invalid synthetic values;
- logs may record that authentication occurred without recording the secret;
- local Wi-Fi credentials follow the repository's documented out-of-tree secret contract;
- the iPhone Wi-Fi provisioning experiment stores saved credentials only in the device Keychain and must not emit them to public diagnostics.

## Reporting vulnerabilities

Do not publish exploit details, secrets, private endpoints, affected infrastructure, or personal information in a public issue.

Until a dedicated private disclosure channel exists, open only a minimal public report stating that a security issue is available, without reproduction details. A private follow-up channel can then be established.

## Explicitly unsupported security claims

BOOTMUX does not currently claim:

- production readiness;
- complete platform isolation;
- resistance to a hostile physical operator;
- secure boot or signed firmware-update completion;
- safe arbitrary shell execution;
- universal terminal parsing;
- universal external-service simulation;
- validated autonomous recovery;
- freedom-to-operate, patentability, optimality, or world-first conclusions.

## Supported versions

No version is currently supported for security-critical use.