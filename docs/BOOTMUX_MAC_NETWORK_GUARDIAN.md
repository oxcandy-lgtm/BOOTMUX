# BOOTMUX macOS Network Guardian (R7C P2)

Recovery-only host controller that restores a macOS host to a clean network
state after a BOOTMUX USB-network session ends or a firmware fault leaves stale
state behind. **It never initiates a BOOTMUX connection and never deletes
anything it does not own.**

Authoritative specification: BOOTMUX PR #6 NX comment
**"R7C P2 MAC GUARDIAN ONLY"**.

---

## 1. Purpose and scope

Older / experimental BOOTMUX USB-network firmware can leave macOS holding:

* a default route via the BOOTMUX peer gateway (`10.77.0.1`),
* scoped routes on the BOOTMUX interface,
* a BOOTMUX network service that is still enabled and/or ordered first,
* a Wi-Fi interface whose IPv4 mode, DNS, or association was disturbed.

The guardian detects this state and repairs it **without a reboot**, restoring
the host to a previously captured baseline. Scope is strictly the macOS host
network stack. Firmware (P1), the regression checker (P3), and on-device tests
(P4) are out of scope for P2.

## 2. Safety model

| Rule | Enforcement |
| --- | --- |
| Recovery-only; never starts a BOOTMUX session | No code path creates routes/services; only removes/restores. |
| Never deletes a network service | R2 uses `-setnetworkserviceenabled … off` only. |
| Never flushes the global routing table | R1 deletes individual routes by gateway/destination, never `route flush`. |
| Never invents configuration | R3/R4/R5 act only from a captured baseline; no baseline ⇒ no IPv4/DNS/order change. |
| Never converts manual → DHCP (or vice versa) without a baseline saying so | R3 restores the exact baseline mode and exact manual values. |
| Never touches unrelated interfaces/services | All commands are scoped to the proven BOOTMUX interface/service or the baseline Wi-Fi service; tests assert zero unrelated commands. |
| Fail-closed on bad state | Hardened state store rejects symlinks, wrong mode/owner, and schema violations. |
| Bounded, idempotent | Repair is diff-driven; a second pass is a no-op. Wi-Fi toggle has a cooldown. |
| No secret leakage | SSID is redacted in all status/log output. |

## 3. Identity proof

A mutation target is acted on only when BOOTMUX ownership is **proven**:

* **Proven** — a USB device matching BOOTMUX VID:PID/product/serial is present
  AND a network interface in `10.77.0.0/24` exists. Repair proceeds.
* **Ambiguous** — a `10.77.0.0/24` interface exists but no hardware signal.
  Audit-only; **no mutation**.
* **Absent** — no BOOTMUX surface. No-op (a stale route may still be removed
  conservatively by gateway match — see R1).

## 4. Repair stages R1–R7

| Stage | Action | Command shape |
| --- | --- | --- |
| R1 | Remove only BOOTMUX-owned routes (default + scoped) | `route -n delete default 10.77.0.1`, `route -n delete -net … -ifscope enN` |
| R2 | Disable only the proven BOOTMUX service | `networksetup -setnetworkserviceenabled "<name>" off` |
| R3 | Restore baseline Wi-Fi IPv4 mode | `ipconfig set enN DHCP` or `networksetup -setmanual "<svc>" ip mask router` |
| R4 | Restore baseline DNS / search domains (automatic vs explicit preserved) | `networksetup -setdnsservers "<svc>" …|Empty`, `-setsearchdomains …|Empty` |
| R5 | Restore baseline service order + enabled states (BOOTMUX service excluded) | `networksetup -ordernetworkservices …`, `-setnetworkserviceenabled … on` |
| R6 | Wi-Fi power cycle as a **last resort** with cooldown | `networksetup -setairportpower enN off|on`, `-setairportnetwork enN <redacted>` |
| R7 | Verify all invariants; classify honestly | read-only checks |

R6 fires only when R1–R5 cannot satisfy verification, and at most once per
cooldown window, to avoid a power-cycle loop.

## 5. Verification contract (R7)

`verify()` returns a stable key set used by tests, docs, and status output:

```
bootmux_default_route_absent
bootmux_scoped_routes_absent
bootmux_service_disabled
wifi_power_matches_baseline
wifi_ssid_matches_baseline_or_redacted_equivalent
wifi_ipv4_mode_matches_baseline
wifi_default_route_restored
wifi_dns_matches_baseline
service_order_matches_baseline
unrelated_services_unchanged
```

Classification: `REPAIRED` (all keys true) or `INCOMPLETE:<first-failed-key>`.
A failed command yields an honest `INCOMPLETE` — never a faked green.

## 6. State store hardening

State lives in `/var/db/bootmux-network-guardian` (0700 root:wheel). The store:

* rejects a directory that is not 0700 root-owned,
* rejects symlinked state files,
* rejects files with the wrong mode/owner,
* validates a schema version on read,
* writes atomically (temp file + rename).

Any violation raises `StateStoreError`; `repair_once` converts it to a
`fail_closed` report and performs **no mutation**.

## 7. Test matrix (T01–T20)

All tests run against `FakeHost` — the developer Mac is never mutated. Each
test asserts the **exact command plan** (argv) and forbids unrelated commands.

| Test | Guarantees |
| --- | --- |
| T01 | Safe HID-only attachment is a complete no-op. |
| T02 | No BOOTMUX ⇒ no-op; baseline captured only after stability window. |
| T03 | Ambiguous 10.77 interface ⇒ audit-only, no mutation. |
| T04 | Proven default route removed; unrelated default route untouched. |
| T05 | All scoped BOOTMUX routes removed; unrelated routes/interfaces untouched. |
| T06 | Detach with DHCP baseline restores DHCP. |
| T07 | Detach with manual baseline restores exact manual values (no DHCP conversion). |
| T08 | Explicit DNS baseline restored exactly. |
| T09 | Automatic DNS baseline clears BOOTMUX-injected DNS (`Empty`). |
| T10 | Contaminated service order restored exactly (unrelated relative order). |
| T11 | Unrelated Ethernet/VPN/Tailscale services unchanged. |
| T12 | Repair succeeds without a Wi-Fi toggle when R1–R5 suffice. |
| T13 | Verification failure ⇒ exactly one bounded toggle + rejoin. |
| T13b | Toggle cooldown prevents a power-cycle loop. |
| T14 | Repeated repair is idempotent (second pass is a no-op). |
| T15 | Daemon restart with a valid snapshot continues from stored baseline. |
| T16 | Corrupt/symlink/wrong-owner/schema-invalid state fails closed, no mutation. |
| T17 | Stale route with hardware absent removed conservatively by gateway. |
| T18 | No baseline ⇒ removes only proven state, invents nothing. |
| T19 | Command failure ⇒ bounded, honest `INCOMPLETE`, not faked green. |
| T20 | Uninstall removes daemon state; unrelated files untouched; evidence preserved. |

Run: `python3 -m unittest discover -s scripts/macos/tests -v`

## 8. Operations

```bash
# Install (root). Idempotent.
sudo scripts/macos/install-bootmux-network-guardian.sh

# Read-only status (SSID redacted).
scripts/macos/bootmux-network-guardian-status.sh

# One bounded manual repair.
sudo /Library/Application\ Support/BOOTMUX/network-guardian/bootmux-network-guardian.py --repair-now

# Uninstall, preserving state evidence.
sudo scripts/macos/uninstall-bootmux-network-guardian.sh
# …or remove state outright:
sudo scripts/macos/uninstall-bootmux-network-guardian.sh --purge
```

## 9. Files

```
scripts/macos/bootmux-network-guardian.py            guardian (CLI + daemon + library)
scripts/macos/tests/test_bootmux_network_guardian.py T01–T20 fixture-driven tests
scripts/macos/launchd/com.bootmux.network-guardian.plist  LaunchDaemon definition
scripts/macos/install-bootmux-network-guardian.sh    idempotent installer
scripts/macos/uninstall-bootmux-network-guardian.sh  idempotent uninstaller
scripts/macos/bootmux-network-guardian-status.sh     read-only status probe
```
