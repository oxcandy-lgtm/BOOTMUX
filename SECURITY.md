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

Model output is treated as untrusted input.

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
- execute arbitrary downloaded code without verification and approval.

## Credential handling

- Authentication remains user-controlled.
- Passwords and tokens must not be placed in model prompts.
- Companion must redact credential-like values before transmitting terminal context.
- Logs and evidence must record that authentication occurred without recording the secret.
- Public fixtures must use invalid placeholder values.

## Reporting vulnerabilities

Do not publish exploit details or sensitive environment data in a public issue.

Until a dedicated private disclosure channel is established, open a minimal public issue stating that a security report is available, without including reproduction details, secrets, affected infrastructure, or personal contact information. Project maintainers can then establish a private follow-up channel.

## Supported versions

No version is currently supported for security-critical use.
