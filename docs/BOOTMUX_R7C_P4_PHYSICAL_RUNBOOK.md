# R7C P4 — Physical Acceptance Runbook

**Scope:** physical acceptance only. Parent HEAD `9ab8b7e8fe5c96ca891df4c88f92fc2dfe1802bb`.
PR #6 stays Draft / open / unmerged. P1–P3 frozen; P5 not started.

This runbook separates **agent-executed read-only commands** from **user physical
actions**. No step claims GREEN unless physically observed. All evidence is
sanitized (no SSID, MAC, IP, gateway, DNS server, serial number, or credential).

## Hard prohibitions (from NX P4)

- No WSR firmware/NAND/bootloader/U-Boot write, factory reset, or OpenWrt install.
- No re-flash of the harmful legacy S3 firmware for reproduction.
- No Mac reboot as a recovery mechanism.
- No deletion of saved Wi-Fi networks or macOS network services.
- No global routing-table flush.
- No disable/reorder of unrelated Ethernet/VPN/Tailscale/Thunderbolt services.
- No SSID/Wi-Fi password/MAC/public IP/private key/BLE credential in evidence.
- No GREEN for a step not physically observed.

## Pre-existing state (honestly reported)

- A `BOOTMUX Bridge` network service on `en8` is ALREADY present and enabled,
  with the S3 detached. This predates P4. The baseline-equality model still
  validates safe-profile cycles (the service is in both baseline and current),
  but the NX "BOOTMUX services expected absent" clean-state expectation is NOT
  met at start. Reported, not hidden.

## Tools (all read-only unless noted)

| Tool | Purpose |
|---|---|
| `scripts/macos/bootmux-physical-oracle.py` | sanitized baseline capture + invariant compare |
| `scripts/macos/bootmux-usb-identity-oracle.py` | USB product/serial/HID/network-class verdict |
| `scripts/macos/bootmux-serial-marker-oracle.py` | firmware serial marker + panic check |
| `scripts/macos/install-bootmux-network-guardian.sh` | install Guardian LaunchDaemon (MUTATES, needs sudo) |

---

## P4-0 — preflight and baseline  [agent + user]

- [x] Prove local = origin = PR HEAD = parent HEAD.
- [x] Confirm PR #6 Draft/open/unmerged.
- [x] Confirm Mac associated with L11 Wi-Fi, Internet healthy.
- [x] Capture sanitized baseline (`/tmp/bmx_p4_evidence/baseline_pre_s3.json`).
- [x] Run Guardian audit + self-test (no mutation).
- [ ] **USER DECISION:** install Guardian LaunchDaemon via documented installer
      (requires sudo + physical admin auth). Deferred until user approves.
- [x] Prefer USB-UART/COM for flashing; native USB detached until attach gates.

## P4-1 — legacy firmware recovery  [conditional]

Only if the affected legacy firmware is ALREADY on the S3. Do not install it.

1. USER: attach S3 once via native USB.
2. AGENT: `bootmux-usb-identity-oracle.py live` + `bootmux-physical-oracle.py capture`.
3. If contamination: prove Guardian detects + restores baseline without reboot.
4. Verify all P2 R7 keys after repair.
5. USER: unplug S3. AGENT: verify repaired state stable.

Classification: `GREEN | SKIPPED_LEGACY_NOT_PRESENT | RED`.

## P4-2 — safe HID-only physical acceptance  [agent build + user flash/attach]

1. [x] Clean safe-profile build from exact parent HEAD (background).
2. [x] Record artifact SHA-256 + size.
3. USER: flash safe profile to S3 via USB-UART/COM (`esptool.py` / `idf.py flash`).
4. USER: attach S3 via native USB. AGENT: `bootmux-usb-identity-oracle.py live`
   must return `SAFE_HID_ONLY`; `bootmux-physical-oracle.py compare --require-clean`
   must hold; serial log must contain `BOOTMUX_USB_NETWORK_SAFE_OFF`, no panic.
5. USER+AGENT: repeat native-USB attach/detach 10×; each cycle compare invariants
   + bounded L11-gateway + Internet-health probes.
6. After 10th detach: wait through Guardian observation window; prove no mutation.
7. USER: one real sleep/wake (after preserving work). AGENT: repeat checks.
   If sleep/wake cannot be done safely → gate PENDING, not invented GREEN.

## P4-3 — experimental fail-closed physical acceptance  [agent build + user]

1. [x] Clean experimental-profile build from same HEAD (background).
2. USER: flash experimental profile. AGENT: on first attach (no S3 Wi-Fi, no
   lease) prove gate DOWN, NAPT/proxy OFF, netif DOWN, no DHCP/DNS/default-route,
   Mac Internet stays on L11.
3. USER: provision S3 only to WSR stock 2.4 GHz SSID. Mac stays on L11.
   Credential NEVER in CLI/env/log/evidence/git.
4. USER: establish explicit 60s lease via authorized BLE/router-spike control.
   If no authorized physical control client exists → `YELLOW_CONTROL_CLIENT_MISSING`,
   stop subsection; do not build a new product feature inside P4.
5. USER+AGENT: configure only static USB-host address + destination-scoped routes.
   No default route, no DNS.
6. Prove path opens only when all four P1 conditions true.
7. Independently drop each condition; prove reverse-order withdrawal
   (proxy → NAPT → netif): NET_RELEASE, lease expiry, S3 Wi-Fi loss,
   WSR power-off (no firmware/config mutation), BLE disconnect.
8. Each loss: path closes within bound; Mac L11 Internet healthy.
9. Restore all four; prove reopen only after a NEW explicit lease.

## P4-4 — active-session S3 detach + Guardian recovery  [user + agent]

With experimental path legitimately active:
1. AGENT: capture sanitized pre-detach state.
2. USER: physically unplug S3 native USB.
3. AGENT: prove Guardian detects detach/heartbeat loss, runs only needed R1–R7.
4. Prove without reboot: BOOTMUX routes absent, service disabled/non-authoritative,
   baseline Wi-Fi IPv4/DNS/service-order restored, L11 + Internet restored,
   unrelated services unchanged, second Guardian pass is a no-op.
5. Repeat active-session detach/recovery 3×.

## P4-5 — evidence + regression rerun  [agent]

Commit only sanitized evidence/reporting + narrowly necessary oracle tooling.
Never commit raw system_profiler/scutil/ifconfig/route/BLE/Wi-Fi dumps.

Required reruns at final HEAD:
- P1 host tests T1–T16
- safe + experimental clean builds
- P2 py_compile, 22 unittests, self-test, bash -n, plutil -lint
- P3 py_compile, M01–M12 mutations, real-tree BOOTMUX_CONTRACT_SYNC=PASS
- credential/secret/privacy scan of all P4 additions
- local/origin/PR HEAD sync proof
- PR Draft/open/unmerged proof

## Stop conditions (report RED/YELLOW, no destructive retries)

- Mac default route leaves L11 during a safe-profile test.
- An unrelated network service is mutated.
- Guardian identity ambiguous but mutation occurs.
- Safe profile enumerates any USB Ethernet class.
- A failed gate condition leaves proxy/NAPT/netif active.
- Recovery would require a Mac reboot.
- Credentials/personal network identifiers enter logs/evidence.
- Physical control for the 60s lease is unavailable.
