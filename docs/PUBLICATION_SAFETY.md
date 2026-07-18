# Publication Safety

This repository is public. All contributions, generated files, screenshots, fixtures, logs, pull-request descriptions, and release artifacts must be safe for unrestricted publication.

## Never commit

- API keys, passwords, tokens, cookies, credentials, or recovery codes;
- private keys, certificates containing private material, or signing secrets;
- personal email addresses, phone numbers, postal addresses, or account identifiers;
- private hostnames, server names, VPN names, internal repository names, or private URLs;
- public or private IP addresses copied from a real environment;
- absolute paths containing a real user or organization name;
- device serial numbers, Bluetooth addresses, hardware UUIDs, or mobile identifiers;
- raw terminal history from a real machine;
- production configuration, database contents, access logs, or crash dumps;
- screenshots showing notifications, account names, browser profiles, or unrelated applications;
- model prompts or transcripts containing private project context.

## Use synthetic placeholders

Preferred:

```text
<target-host>
<approved-target-path>
<redacted-token>
example.invalid
192.0.2.10
2001:db8::10
example_user
```

Avoid placeholders that accidentally reproduce real values.

## Documentation rules

- Describe capabilities without publishing private deployment details.
- Use generic operating-system paths or bracketed placeholders.
- Do not include shell history copied from a personal machine.
- Do not claim unimplemented or unverified behavior as complete.
- Mark experimental routes and platform assumptions explicitly.
- Do not embed tracking pixels, analytics identifiers, or private document links.

## Code and fixture rules

- Secrets must be read from local environment or an approved secret store.
- Example environment files must contain names only, never usable values.
- Test credentials must be clearly invalid and scoped to fixtures.
- Generated logs must pass redaction before being saved as artifacts.
- Session identifiers must be random and must not encode personal data.
- Device discovery must avoid persisting globally unique hardware identifiers unless strictly required and user-approved.
- Debug builds must not print full BLE payloads or terminal buffers by default.

## Pull-request checklist

Before every public PR:

- [ ] Search for email-address patterns.
- [ ] Search for private-key and token markers.
- [ ] Search for absolute home-directory paths.
- [ ] Search for real hostnames and infrastructure names.
- [ ] Search for IPv4 and IPv6 addresses; confirm only documentation ranges are present.
- [ ] Inspect screenshots and binary assets manually.
- [ ] Confirm logs are synthetic or redacted.
- [ ] Confirm PR title and body contain no private context.
- [ ] Confirm examples use placeholders.
- [ ] Confirm experimental claims are labeled accurately.

## Recommended automated checks

A future public-safety check should fail closed on:

```text
private key headers
common token prefixes
credential assignments with non-placeholder values
email addresses outside an explicit documentation allowlist
home-directory paths containing non-placeholder user names
unknown IP addresses
private top-level domains or infrastructure suffixes
high-entropy strings near secret-related variable names
```

Allowlist exceptions must be narrow, documented, and test-covered. A broad ignore file must not become a mechanism for silently publishing sensitive material.

## Incident response

If sensitive material is committed:

1. stop further publication;
2. rotate or revoke the exposed secret immediately;
3. remove the material from the active branch;
4. assess whether repository history must be rewritten;
5. document the incident without repeating the sensitive value;
6. add a regression rule or test when appropriate.

Deleting a file from the latest commit does not erase it from repository history.
