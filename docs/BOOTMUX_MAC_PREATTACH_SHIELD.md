# BOOTMUX Mac Pre-Attach Shield (R7C P4-R0B — Ephemeral Edition)

## Purpose

One-shot macOS network protection for the dangerous legacy ESP32-S3 replacement.
After the S3 is reflashed safe and the session is closed, the Mac returns to its
**exact pre-install network behavior**. No permanent policy remains.

This supersedes P4-R0. The shield is NOT a permanent machine policy.

## Lifecycle

```text
NOT_INSTALLED
  -> install
INSTALLED_DISARMED
  -> arm --ttl 1800
ARMED_TEMPORARY
  -> safe S3 replacement work
  -> close-session
RESTORED
  -> uninstall --purge
NOT_INSTALLED / PRESTATE_EQUIVALENT
```

The shield must never be armed indefinitely.

## TTL Bounds

| Parameter | Value |
|---|---|
| Default TTL | 1800 s (30 min) |
| Maximum TTL | 7200 s (2 hours) |
| Minimum TTL | 60 s |
| Zero/infinite | Rejected (clamped) |

The daemon automatically executes exact rollback when TTL expires.
Reboot with an expired/armed session triggers rollback before normal monitoring.

## Network Location Isolation

If supported (`networksetup -createlocation` available), the shield creates a
temporary Network Location `BOOTMUX-SHIELD-<session-id>` and applies all
mutations inside it. On close, it switches back to the original location and
deletes the temporary one.

If not supported or unstable, falls back to baseline/restore with field-by-field
exact restoration.

## Exact Mutation Journal

Before each mutation, an append-only journal records the exact pre-value:
- Network location, Wi-Fi power/service/IPv4/IPv6/DNS/search
- Complete service order and enabled/disabled states
- Each route added/removed
- PF pre-state, anchor rules, enable reference
- Launchd pre-state, installed files

Rollback replays the journal in reverse. **Never infers an old value.**
Unknown pre-value → `INCOMPLETE_ROLLBACK_UNKNOWN_PRESTATE`.

## Close Session Order (C1–C12)

```text
C1  stop quarantine daemon
C2  remove shield-owned PF anchor rules
C3  release PF enable reference (preserve pre-existing PF)
C4  remove shield-added IPv4/IPv6 split routes
C5  restore exact enabled state of every modified service
C6  restore exact original service order
C7  restore exact Wi-Fi IPv4/IPv6 mode and values
C8  restore exact DNS/search automatic-or-explicit state
C9  switch back to original Network Location (if isolated)
C10 delete temporary shield location
C11 verify pre-state equivalence (fingerprint comparison)
C12 mark session closed
```

## Purge

`uninstall --purge` removes only BOOTMUX shield-owned artifacts:
- LaunchDaemon plist + job
- Installed shield script + empty parent dirs
- State directory (sessions, logs, journal)
- PF anchor rules

After purge, a normal USB Ethernet adapter is handled by stock macOS with no
BOOTMUX interception.

## Fixes from P4-R0 (Section F)

| ID | Fix |
|---|---|
| F1 | `cmd_disarm()` → `close_session()` restores all service states + order |
| F2 | Automatic DNS restored as `Empty`, not skipped |
| F3 | Manual IPv4/IPv6 restored exactly via journal |
| F4 | Never call `-setairportnetwork` with SSID digest |
| F5 | PF pre-state tracked; shield does not leave PF enabled |
| F6 | BOOTMUX identification requires proven device/service mapping |
| F7 | `pf_anchor_active` and service records reflect actual mutations |

## Tests

E01–E20 (42 test methods) covering:
- DHCP/manual IPv4/IPv6/DNS/search exact roundtrip
- Service order and enabled-state restoration
- PF pre-state (enabled/disabled) preservation
- TTL bounds, expiry, reboot recovery
- Idempotent close/purge
- Device-present block / device-absent close
- Journal unknown-prestate fail-closed
- Fingerprint comparison
- Network Location isolation
- F4/F5/F6 regression guards

## Hard Gates

No S3 attach, no flash, no service delete, no global route/PF flush,
no saved-Wi-Fi delete, no unrelated service mutation, no permanent deny,
no inferred rollback values.
