# BOOTMUX Mac Pre-Attach Shield (R7C P4-R0)

## Purpose

Pre-emptive macOS network protection that runs **before** the ESP32-S3 cable is
inserted.  Complements P2 Guardian (post-fault recovery) by denying new external
Ethernet authority, pinning Wi-Fi routes, and quarantining stale BOOTMUX state.

The shield operates entirely offline — no Internet or WORKER dependency after arm.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  bootmux-attach-shield.py  (root LaunchDaemon)  │
│                                                 │
│  ┌───────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Baseline  │  │ Quarantine│  │ Event Loop  │  │
│  │ Capture A │  │ BOOTMUX B │  │ Watchdog F  │  │
│  └───────────┘  └──────────┘  └─────────────┘  │
│  ┌───────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ PF Anchor │  │ Route Pin│  │ Recovery    │  │
│  │ Section C │  │ Section E│  │ Q1–Q9 G     │  │
│  └───────────┘  └──────────┘  └─────────────┘  │
│  ┌───────────┐  ┌──────────┐                    │
│  │ Wi-Fi Lock│  │ Forensic │                    │
│  │ Section D │  │ Log H    │                    │
│  └───────────┘  └──────────┘                    │
└─────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|---|---|
| `bootmux-attach-shield.py` | Main shield controller (8 modes) |
| `install-bootmux-attach-shield.sh` | Install LaunchDaemon (sudo) |
| `uninstall-bootmux-attach-shield.sh` | Disarm + remove (sudo) |
| `bootmux-attach-shield-status.sh` | Read-only status (no sudo) |
| `launchd/com.bootmux.attach-shield.plist` | LaunchDaemon definition |
| `tests/test_bootmux_attach_shield.py` | S01–S20 fixture tests |

## Modes

| Mode | Description |
|---|---|
| `--audit` | Read-only audit of current network state |
| `--arm` | Capture baseline, quarantine, pin routes, persist state |
| `--disarm` | Remove pinned routes, PF anchor, stop daemon |
| `--status` | Show armed/disarmed state |
| `--recover-now` | Run Q1–Q9 recovery immediately |
| `--postmortem` | Generate sanitized forensic report |
| `--daemon` | Run as LaunchDaemon (event loop + watchdog) |
| `--self-test` | Internal consistency checks |

## Lifecycle

```
install → arm → [daemon running] → status → recover-now → disarm → uninstall
```

## PF Anchor

Uses dedicated anchor `com.bootmux.attach-shield`.  Never replaces `/etc/pf.conf`,
never flushes unrelated anchors.  Rollback removes only owned rules.

## Route Pinning (Section E)

Split-default routes (`0.0.0.0/1` + `128.0.0.0/1`) through the Wi-Fi gateway.
Validated against local `route(8)` before applying.  If validation fails,
returns `YELLOW_ROUTE_PIN_UNAVAILABLE` and relies on service pre-disable + PF +
event-driven repair.

## State Store

- Location: `/var/db/bootmux-shield/` (root-owned, 0700)
- Files: 0600, no symlinks, atomic writes, bounded size
- Sessions: `/var/db/bootmux-shield/sessions/<id>/shield.jsonl`

## Hard Safety Gates

- No S3 attachment before shield GREEN
- No S3 flash in this phase
- No network service deletion
- No global route/PF flush
- No saved Wi-Fi deletion or password export
- No unrelated service mutation
- No WORKER/Internet dependency after arm
- No disarm while untrusted device present

## Privacy

All logs and evidence are sanitized: no SSID plaintext, MAC addresses, serial
numbers, private paths, or credentials.  SSID stored as SHA-256 digest prefix.
