# BOOTMUX Safe Flash Preflight (R7C P4-R1)

## Scope

P4-R1 is **offline safe-flash preflight only**.  No ESP32-S3 connection,
power, enumeration, Download Mode transition, reset, or firmware write.

Status: `READY_UNARMED` / `ATTACH_AUTHORITY=BLOCKED_PENDING_P4_R2`

## Artifacts

| File | Purpose |
|---|---|
| `firmware/esp32s3-router-spike/safe-flash-manifest.json` | Pinned flash offsets, sizes, SHA-256, USB identity, forbidden/required strings |
| `scripts/macos/bootmux-safe-flash-inspect.py` | Binary string scan: NCM/ECM/RNDIS/DHCP/NAPT/IP-fwd ABSENT, safe marker GREEN |
| `scripts/macos/bootmux-safe-flash-runner.py` | One-shot runner: shield→arm(TTL 1800)→serial detect→flash→verify→close→purge |
| `scripts/macos/bootmux-offline-rescue-bundle.sh` | Self-contained offline bundle (no Internet, no WORKER) |
| `scripts/macos/tests/test_bootmux_safe_flash.py` | Focused tests F01-F23 |

## Safe HID-only profile

- `CONFIG_BOOTMUX_USB_NETWORK_EXPERIMENTAL` is **not set** (sdkconfig line 534)
- USB identity: VID `0x303A`, PID `0x4014`, Product `BOOTMUX Keyboard Safe`, Serial `BOOTMUX-HID-SAFE`
- Device class `0x00` (per-interface), no IAD, no CDC/NCM/ECM/RNDIS descriptors
- No DHCP server, no NAPT, no IP forwarding in the safe profile

## Flash offsets (pinned)

| Artifact | Offset | Size | SHA-256 |
|---|---|---|---|
| bootloader | `0x0` | 21088 | `a2adba9b...7918bb` |
| partition-table | `0x8000` | 3072 | `7f00b6c0...b7c820` |
| application | `0x10000` | 989936 | `97b95053...5fe31a` |

Flash params: `dio` / `80m` / `2MB`

## Runner pipeline (P4-R2 execution)

```
PRE_FINGERPRINT → SHIELD_INSTALL → SHIELD_ARM(TTL 1800)
→ SERIAL_BASELINE → WAIT_FOR_DEVICE → SERIAL_DETECT
→ ROM_MODE_CHECK → FLASH → FLASH_VERIFY → SAFE_IDENTITY_VERIFY
→ SHIELD_CLOSE → SHIELD_PURGE → POST_FINGERPRINT → FINGERPRINT_COMPARE
```

### Serial port rules

- Before/after diff; **exactly 1 candidate** allowed
- USB-UART/COM preferred (`cu.usbserial-*`, `cu.usbmodem*`, `cu.SLAB_*`, `cu.wchusbserial*`)
- Rejected: Bluetooth, phones, storage, network interfaces, BOOTMUX network devices
- Single-port: ROM Download Mode confirmed before write permission

### Crash recovery

- Append-only journal at `/var/db/bootmux-flash-runner/<session>/journal.jsonl`
- `fsync` after every entry
- Resume: `--resume <session-id>` — detects last event, closes armed shield, cleans up
- Flash failure / WORKER loss / Internet loss / terminal exit → journal survives → safe rollback

### Shield integration

- Untrusted S3 connected → shield disarm **blocked**
- All steps complete → `close-session` → `uninstall --purge` → pre/post fingerprint match required

## Offline rescue bundle

```bash
bash scripts/macos/bootmux-offline-rescue-bundle.sh [bundle_dir] [tarball_path]
```

Creates a self-contained tarball with all scripts, tests, firmware binaries,
manifest, and docs.  **Zero network dependency.**  Works if Internet and
WORKER are both gone.

## P4-R0C disposition

```yaml
normal_usb_ethernet_physical_proof: SKIPPED_HARDWARE_UNAVAILABLE
claimed_green: false
owner_risk_acceptance: true
blocks_s3_rescue: false
```

## Hard gates

- No S3 attach/power/enumerate/flash in P4-R1
- No Internet dependency in bundle or runner
- No WORKER dependency
- No inferred rollback values
- No permanent network mutation
- PR #6 stays Draft / open / not merged
