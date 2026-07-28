#!/usr/bin/env python3
"""R7C P4-R1 — BOOTMUX Safe Flash Runner (one-shot, journal-backed).

Orchestrates: shield install → arm(TTL 1800) → serial detect → flash →
safe-identity verify → close-session → uninstall --purge → fingerprint check.

P4-R1 scope: runner is implemented but NOT executed.  Status = READY_UNARMED.
Actual flash is deferred to P4-R2 (ATTACH_AUTHORITY=BLOCKED_PENDING_P4_R2).

Fully offline.  No Internet, no WORKER dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
FIRMWARE_DIR = REPO_ROOT / "firmware" / "esp32s3-router-spike"
SHIELD_SCRIPT = SCRIPT_DIR / "bootmux-attach-shield.py"
INSPECT_SCRIPT = SCRIPT_DIR / "bootmux-safe-flash-inspect.py"
MANIFEST_PATH = FIRMWARE_DIR / "safe-flash-manifest.json"
JOURNAL_DIR = Path("/var/db/bootmux-flash-runner")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TTL_SECONDS = 1800  # 30 minutes

# Serial device patterns (macOS)
SERIAL_GLOB_PATTERNS = [
    "/dev/cu.usbserial-*",
    "/dev/cu.usbmodem*",
    "/dev/cu.SLAB_*",
    "/dev/cu.wchusbserial*",
]

# Rejection patterns — devices that must NEVER be flashed
REJECT_PATTERNS = [
    re.compile(r"Bluetooth", re.IGNORECASE),
    re.compile(r"iPhone|iPad|Android|Samsung|Pixel|Xiaomi", re.IGNORECASE),
    re.compile(r"disk[0-9]", re.IGNORECASE),
    re.compile(r"BOOTMUX.*Bridge|BOOTMUX.*NCM|BOOTMUX.*ECM", re.IGNORECASE),
    re.compile(r"en[0-9]", re.IGNORECASE),  # network interfaces
    re.compile(r"bridge[0-9]", re.IGNORECASE),
]

# ROM Download Mode marker in serial output
ROM_DOWNLOAD_MARKER = "waiting for download"
ROM_DOWNLOAD_ALT = "ESP-ROM:esp32s3"


# ---------------------------------------------------------------------------
# Journal (crash-safe, local-only)
# ---------------------------------------------------------------------------

@dataclass
class JournalEntry:
    seq: int
    ts: float
    event: str
    data: Dict[str, Any] = field(default_factory=dict)
    status: str = "OK"


class FlashJournal:
    """Append-only local journal for crash recovery."""

    def __init__(self, session_id: str, journal_dir: Path = JOURNAL_DIR):
        self.session_id = session_id
        self.journal_dir = journal_dir
        self.session_dir = journal_dir / session_id
        self.journal_path = self.session_dir / "journal.jsonl"
        self._seq = 0

    def init(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.session_dir, 0o700)

    def append(self, event: str, data: Optional[Dict[str, Any]] = None,
               status: str = "OK") -> JournalEntry:
        self._seq += 1
        entry = JournalEntry(
            seq=self._seq, ts=time.time(), event=event,
            data=data or {}, status=status,
        )
        with open(self.journal_path, "a") as f:
            f.write(json.dumps(asdict(entry), default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return entry

    def load(self) -> List[JournalEntry]:
        entries = []
        if not self.journal_path.exists():
            return entries
        for line in self.journal_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            entries.append(JournalEntry(**d))
        return entries

    def last_event(self) -> Optional[str]:
        entries = self.load()
        return entries[-1].event if entries else None

    def can_resume_from(self, event: str) -> bool:
        """Check if journal shows we can safely resume after `event`."""
        entries = self.load()
        event_names = [e.event for e in entries]
        return event in event_names


# ---------------------------------------------------------------------------
# Serial port detection
# ---------------------------------------------------------------------------

def list_serial_ports() -> List[str]:
    """List current serial port devices matching known patterns."""
    ports = []
    for pattern in SERIAL_GLOB_PATTERNS:
        import glob
        ports.extend(glob.glob(pattern))
    return sorted(set(ports))


def is_rejected_device(port: str) -> Tuple[bool, str]:
    """Check if a serial port matches a rejection pattern."""
    for pat in REJECT_PATTERNS:
        if pat.search(port):
            return True, f"matches reject pattern: {pat.pattern}"
    return False, ""


def detect_new_port(before: List[str], after: List[str]) -> Tuple[Optional[str], str]:
    """Detect exactly one new serial port from before/after diff.

    Returns (port, reason).  port is None if not exactly 1 candidate.
    """
    new_ports = [p for p in after if p not in before]

    # Filter rejected devices
    candidates = []
    rejected = []
    for p in new_ports:
        rej, reason = is_rejected_device(p)
        if rej:
            rejected.append((p, reason))
        else:
            candidates.append(p)

    if len(candidates) == 0:
        if rejected:
            return None, f"REJECTED: all new ports rejected: {rejected}"
        return None, "NO_NEW_PORT: no new serial device detected"

    if len(candidates) > 1:
        return None, f"AMBIGUOUS: {len(candidates)} candidates: {candidates}"

    return candidates[0], "SINGLE_CANDIDATE"


def check_rom_download_mode(port: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """Check if the device on `port` is in ESP32 ROM Download Mode.

    Reads a few bytes from the serial port looking for ROM markers.
    Returns (is_rom_mode, detail).
    """
    try:
        import serial  # pyserial
    except ImportError:
        return False, "PYSERIAL_MISSING: pip install pyserial required"

    try:
        ser = serial.Serial(port, baudrate=115200, timeout=timeout)
        time.sleep(0.5)
        # Send sync byte to trigger ROM response
        ser.write(b"\xc0")
        time.sleep(0.5)
        data = ser.read(256)
        ser.close()
        text = data.decode("ascii", errors="replace").lower()
        if ROM_DOWNLOAD_MARKER.lower() in text or ROM_DOWNLOAD_ALT.lower() in text:
            return True, "ROM_DOWNLOAD_MODE_CONFIRMED"
        if len(data) > 0:
            return False, f"NOT_ROM_MODE: got {len(data)} bytes, no ROM marker"
        return False, "NO_RESPONSE: device silent"
    except Exception as e:
        return False, f"SERIAL_ERROR: {e}"


# ---------------------------------------------------------------------------
# Flash operations
# ---------------------------------------------------------------------------

def find_esptool(bundle_dir: Optional[Path] = None) -> Optional[List[str]]:
    """Find esptool.py — bundle-local first, then system.

    Returns argv-compatible list for subprocess.run, or None if not found.
    When bundle_dir is provided, checks tools/tool-esptoolpy/ first.
    Verifies the tool by running 'version' before returning.
    """
    candidates: List[Tuple[str, Path]] = []  # (label, path)

    # 1. Bundle-local (highest priority)
    if bundle_dir is not None:
        bundle_esptool = Path(bundle_dir) / "tools" / "tool-esptoolpy" / "esptool.py"
        if bundle_esptool.exists():
            candidates.append(("BUNDLE", bundle_esptool))

    # 1b. Auto-detect bundle root from SCRIPT_DIR (scripts/macos/ -> bundle root)
    bundle_local = SCRIPT_DIR.parent.parent / "tools" / "tool-esptoolpy" / "esptool.py"
    if bundle_local.exists():
        # Only add if not already in candidates
        if not any(c[0] == "BUNDLE" and c[1] == bundle_local for c in candidates):
            candidates.append(("BUNDLE_AUTO", bundle_local))

    # 2. IDF_PATH from env
    idf_path = os.environ.get("IDF_PATH", "")
    if idf_path:
        candidates.append(("IDF_PATH", Path(idf_path) / "components" / "esptool_py" / "esptool" / "esptool.py"))

    # 3. System locations
    candidates.extend([
        ("HOME_ESPRESSIF", Path.home() / ".espressif" / "python_env" / "idf_py" / "bin" / "esptool.py"),
        ("USR_BIN", Path("/usr/local/bin/esptool.py")),
        ("HOMEBREW", Path("/opt/homebrew/bin/esptool.py")),
    ])

    # 4. PlatformIO packages (scan common paths)
    pio_packages = Path.home() / ".platformio" / "packages"
    pio_esptool = pio_packages / "tool-esptoolpy" / "esptool.py"
    if pio_esptool.exists():
        candidates.append(("PLATFORMIO", pio_esptool))
    idf_esptool = pio_packages / "framework-espidf" / "components" / "esptool_py" / "esptool" / "esptool.py"
    if idf_esptool.exists():
        candidates.append(("IDF_PIO", idf_esptool))

    # Verify candidates in priority order
    for label, path in candidates:
        if not path.exists():
            continue
        try:
            # For bundle-local esptool, set env to find bundled pyserial
            extra_env = None
            if label.startswith("BUNDLE"):
                tools_dir = path.parent.parent  # tools/tool-esptoolpy/ -> tools/
                if (tools_dir / "serial").exists():
                    extra_env = os.environ.copy()
                    extra_env["PYTHONPATH"] = str(tools_dir) + ":" + extra_env.get("PYTHONPATH", "")
            # Try running as a script with python3
            result = subprocess.run(
                [sys.executable, str(path), "version"],
                capture_output=True, text=True, timeout=10,
                env=extra_env)
            if result.returncode == 0:
                return [sys.executable, str(path)]
        except (subprocess.TimeoutExpired, OSError):
            continue

    # 5. Try which (last resort)
    try:
        result = subprocess.run(["which", "esptool.py"], capture_output=True, text=True)
        if result.returncode == 0:
            return [result.stdout.strip()]
    except OSError:
        pass

    # 6. Try python -m esptool
    try:
        result = subprocess.run([sys.executable, "-m", "esptool", "version"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return [sys.executable, "-m", "esptool"]
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def build_flash_command(esptool_cmd: List[str], port: str, manifest: Dict[str, Any],
                        build_dir: Path) -> List[str]:
    """Build the esptool flash command from manifest.

    esptool_cmd is an argv list (e.g. ['python3', '/path/to/esptool.py']).
    Note: artifact paths in the manifest are relative to FIRMWARE_DIR
    (they include the build-dir prefix), so we join with build_dir.parent.
    """
    flash_params = manifest.get("flash_params", {})
    cmd = list(esptool_cmd) + [
        "--chip", "esp32s3",
        "--port", port,
        "--baud", "460800",
        "--before", "default_reset",
        "--after", "hard_reset",
        "write_flash",
        "--flash_mode", flash_params.get("flash_mode", "dio"),
        "--flash_freq", flash_params.get("flash_freq", "80m"),
        "--flash_size", flash_params.get("flash_size", "2MB"),
    ]
    for art in manifest.get("artifacts", []):
        cmd.extend([art["offset"], str(build_dir.parent / art["path"])])
    return cmd


def verify_flash_sha(port: str, manifest: Dict[str, Any],
                     build_dir: Path) -> Dict[str, Any]:
    """Read back flash and verify SHA-256 (post-flash verification)."""
    esptool_cmd = find_esptool()
    if not esptool_cmd:
        return {"status": "YELLOW", "reason": "ESPTOOL_MISSING"}

    results = []
    for art in manifest.get("artifacts", []):
        offset = int(art["offset"], 16)
        size = art["size"]
        # Read back via esptool read_flash
        cmd = list(esptool_cmd) + [
            "--chip", "esp32s3", "--port", port,
            "read_flash", hex(offset), str(size), "/tmp/bootmux-readback.bin",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            results.append({"name": art["name"], "status": "RED",
                            "reason": f"read_flash failed: {proc.stderr[:200]}"})
            continue

        readback = Path("/tmp/bootmux-readback.bin")
        if not readback.exists():
            results.append({"name": art["name"], "status": "RED", "reason": "readback file missing"})
            continue

        actual_sha = hashlib.sha256(readback.read_bytes()).hexdigest()
        match = actual_sha == art["sha256"]
        results.append({
            "name": art["name"],
            "status": "GREEN" if match else "RED",
            "sha256_match": match,
            "actual": actual_sha,
            "expected": art["sha256"],
        })
        readback.unlink(missing_ok=True)

    overall = "GREEN" if all(r["status"] == "GREEN" for r in results) else "RED"
    return {"status": overall, "artifacts": results}


# ---------------------------------------------------------------------------
# Shield integration
# ---------------------------------------------------------------------------

def run_shield(args: List[str], sudo: bool = True) -> Tuple[int, str]:
    """Run the shield script with given args."""
    cmd = (["sudo"] if sudo else []) + [sys.executable, str(SHIELD_SCRIPT)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc.returncode, proc.stdout + proc.stderr


def shield_is_armed() -> bool:
    """Check if shield is currently armed."""
    rc, out = run_shield(["--status"], sudo=True)
    return "STATUS=ARMED" in out


# ---------------------------------------------------------------------------
# Runner state machine
# ---------------------------------------------------------------------------

RUNNER_STEPS = [
    "INIT",
    "PRE_FINGERPRINT",
    "SHIELD_INSTALL",
    "SHIELD_ARM",
    "SERIAL_BASELINE",
    "WAIT_FOR_DEVICE",
    "SERIAL_DETECT",
    "ROM_MODE_CHECK",
    "PRE_FLASH_GATE",
    "FLASH",
    "FLASH_VERIFY",
    "SAFE_IDENTITY_VERIFY",
    "SHIELD_CLOSE",
    "SHIELD_PURGE",
    "POST_FINGERPRINT",
    "FINGERPRINT_COMPARE",
    "DONE",
]


class SafeFlashRunner:
    """One-shot safe flash runner with journal-backed crash recovery."""

    def __init__(self, session_id: Optional[str] = None, dry_run: bool = True,
                 preflight_only: bool = False):
        self.session_id = session_id or f"flash-{int(time.time()):x}"
        self.dry_run = dry_run
        self.preflight_only = preflight_only
        self.journal = FlashJournal(self.session_id)
        self.manifest: Optional[Dict[str, Any]] = None
        self.build_dir: Optional[Path] = None
        self.serial_port: Optional[str] = None
        self.serial_baseline: List[str] = []
        self.pre_fingerprint: Optional[Dict[str, Any]] = None
        self.post_fingerprint: Optional[Dict[str, Any]] = None
        self._interrupted = False

    def _setup_signal_handlers(self) -> None:
        def handler(signum: int, frame: Any) -> None:
            self._interrupted = True
            self.journal.append("INTERRUPTED", {"signal": signum}, status="WARN")
            print(f"\nINTERRUPTED (signal {signum}). Journal saved. "
                  f"Resume with: --resume {self.session_id}", file=sys.stderr)
            sys.exit(130)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def load_manifest(self) -> bool:
        path = MANIFEST_PATH
        # Fallback: try bundle-relative path
        if not path.exists():
            bundle_root = SCRIPT_DIR.parent.parent
            alt = bundle_root / "firmware" / "esp32s3-router-spike" / "safe-flash-manifest.json"
            if alt.exists():
                path = alt
        if not path.exists():
            print(f"MANIFEST_MISSING: {path}", file=sys.stderr)
            return False
        self.manifest = json.loads(path.read_text())
        # Determine build_dir: prefer bundle-relative when FIRMWARE_DIR doesn't exist
        build_dir_name = self.manifest.get("build_dir", "build-p4-safe")
        candidate = FIRMWARE_DIR / build_dir_name
        if candidate.exists():
            self.build_dir = candidate
        else:
            # Bundle-relative fallback
            bundle_root = path.parent.parent.parent  # firmware/esp32s3-router-spike/ -> bundle root
            # Actually path.parent is firmware/esp32s3-router-spike/
            # and manifest path is inside bundle, so path.parent / build_dir_name
            self.build_dir = path.parent / build_dir_name
        return True

    def step_pre_fingerprint(self) -> str:
        """Capture pre-flash fingerprint via shield --fingerprint."""
        rc, out = run_shield(["--fingerprint"], sudo=False)
        if rc != 0:
            # Shield not installed yet — use direct fingerprint
            rc, out = run_shield(["--fingerprint"], sudo=False)
        try:
            self.pre_fingerprint = json.loads(out)
            fp = self.pre_fingerprint
            self.journal.append("PRE_FINGERPRINT", {"keys": len(fp) if fp else 0})
            return "GREEN"
        except json.JSONDecodeError:
            self.journal.append("PRE_FINGERPRINT", {"error": "parse failed"}, status="RED")
            return "RED"

    def step_shield_install(self) -> str:
        if self.dry_run:
            self.journal.append("SHIELD_INSTALL", {"dry_run": True})
            return "GREEN_DRY_RUN"
        install_script = SCRIPT_DIR / "install-bootmux-attach-shield.sh"
        proc = subprocess.run(["sudo", "bash", str(install_script)],
                              capture_output=True, text=True, timeout=60)
        ok = proc.returncode == 0
        self.journal.append("SHIELD_INSTALL", {"ok": ok, "output": proc.stdout[:500]},
                            status="OK" if ok else "RED")
        return "GREEN" if ok else "RED"

    def step_shield_arm(self) -> str:
        if self.dry_run:
            self.journal.append("SHIELD_ARM", {"dry_run": True, "ttl": TTL_SECONDS})
            return "GREEN_DRY_RUN"
        rc, out = run_shield(["--arm", "--ttl", str(TTL_SECONDS)])
        ok = rc == 0 and "CLASSIFICATION=GREEN" in out
        self.journal.append("SHIELD_ARM", {"ok": ok, "ttl": TTL_SECONDS,
                                           "output": out[:500]},
                            status="OK" if ok else "RED")
        return "GREEN" if ok else "RED"

    def step_serial_baseline(self) -> str:
        self.serial_baseline = list_serial_ports()
        self.journal.append("SERIAL_BASELINE", {"ports": self.serial_baseline})
        return "GREEN"

    def step_serial_detect(self) -> str:
        after = list_serial_ports()
        port, reason = detect_new_port(self.serial_baseline, after)
        if port is None:
            self.journal.append("SERIAL_DETECT", {"reason": reason, "after": after},
                                status="RED")
            return f"RED:{reason}"
        self.serial_port = port
        self.journal.append("SERIAL_DETECT", {"port": port, "reason": reason})
        return "GREEN"

    def step_rom_mode_check(self) -> str:
        if not self.serial_port:
            return "RED:NO_PORT"
        if self.dry_run:
            self.journal.append("ROM_MODE_CHECK", {"dry_run": True, "port": self.serial_port})
            return "GREEN_DRY_RUN"
        is_rom, detail = check_rom_download_mode(self.serial_port)
        self.journal.append("ROM_MODE_CHECK", {"port": self.serial_port,
                                               "is_rom": is_rom, "detail": detail},
                            status="OK" if is_rom else "RED")
        return "GREEN" if is_rom else f"RED:{detail}"

    def step_pre_flash_gate(self) -> str:
        """Authoritative inspection + hash re-verification BEFORE write_flash.

        Runs the inspector as a subprocess and re-verifies every artifact
        hash from disk.  If overall != GREEN, write_flash is NEVER reached.
        """
        if not self.manifest or not self.build_dir:
            return "RED:PRECONDITIONS"

        # 1. Authoritative inspection via inspector subprocess
        proc = subprocess.run(
            [sys.executable, str(INSPECT_SCRIPT),
             "--manifest", str(MANIFEST_PATH), "--json"],
            capture_output=True, text=True, timeout=60)
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.journal.append("PRE_FLASH_GATE",
                                {"error": "inspector json parse failed",
                                 "stderr": proc.stderr[:300]}, status="RED")
            return "RED:INSPECTOR_PARSE_FAILED"

        overall = result.get("overall", "RED")
        if overall != "GREEN":
            self.journal.append("PRE_FLASH_GATE",
                                {"overall": overall,
                                 "safe_off": result.get("safe_off_marker"),
                                 "usb_identity": result.get("usb_identity", {}).get("match"),
                                 "sdkconfig": result.get("sdkconfig_marker")},
                                status="RED")
            return f"RED:INSPECTION_NOT_GREEN:{overall}"

        # 2. Final hash re-verification from disk (independent of inspector)
        for art in self.manifest.get("artifacts", []):
            art_path = self.build_dir.parent / art["path"]
            if not art_path.exists():
                self.journal.append("PRE_FLASH_GATE",
                                    {"error": f"artifact missing: {art_path}"},
                                    status="RED")
                return f"RED:ARTIFACT_MISSING:{art['name']}"
            actual_sha = hashlib.sha256(art_path.read_bytes()).hexdigest()
            if actual_sha != art["sha256"]:
                self.journal.append("PRE_FLASH_GATE",
                                    {"artifact": art["name"],
                                     "expected": art["sha256"],
                                     "actual": actual_sha}, status="RED")
                return f"RED:HASH_MISMATCH:{art['name']}"

        self.journal.append("PRE_FLASH_GATE",
                            {"overall": "GREEN", "artifacts_verified": len(self.manifest["artifacts"])})
        return "GREEN"

    def step_flash(self) -> str:
        if not self.serial_port or not self.manifest or not self.build_dir:
            return "RED:PRECONDITIONS"
        if self.dry_run:
            self.journal.append("FLASH", {"dry_run": True, "port": self.serial_port})
            return "GREEN_DRY_RUN"

        esptool_cmd = find_esptool()
        if not esptool_cmd:
            self.journal.append("FLASH", {"error": "esptool not found"}, status="RED")
            return "RED:ESPTOOL_MISSING"

        cmd = build_flash_command(esptool_cmd, self.serial_port, self.manifest, self.build_dir)
        self.journal.append("FLASH_START", {"cmd": " ".join(cmd[:10]) + "..."})
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        ok = proc.returncode == 0
        self.journal.append("FLASH", {"ok": ok, "returncode": proc.returncode,
                                      "stderr_tail": proc.stderr[-500:]},
                            status="OK" if ok else "RED")
        return "GREEN" if ok else "RED:FLASH_FAILED"

    def step_flash_verify(self) -> str:
        if self.dry_run:
            self.journal.append("FLASH_VERIFY", {"dry_run": True})
            return "GREEN_DRY_RUN"
        if not self.serial_port or not self.manifest or not self.build_dir:
            return "RED:PRECONDITIONS"
        result = verify_flash_sha(self.serial_port, self.manifest, self.build_dir)
        self.journal.append("FLASH_VERIFY", result,
                            status="OK" if result["status"] == "GREEN" else "RED")
        return result["status"]

    def step_safe_identity_verify(self) -> str:
        """Run the inspector to verify safe HID-only identity."""
        proc = subprocess.run(
            [sys.executable, str(INSPECT_SCRIPT), "--manifest", str(MANIFEST_PATH), "--json"],
            capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            self.journal.append("SAFE_IDENTITY_VERIFY", {"error": proc.stderr[:500]},
                                status="RED")
            return "RED"
        try:
            result = json.loads(proc.stdout)
            overall = result.get("overall", "RED")
            self.journal.append("SAFE_IDENTITY_VERIFY", {"overall": overall},
                                status="OK" if overall == "GREEN" else "RED")
            return overall
        except json.JSONDecodeError:
            self.journal.append("SAFE_IDENTITY_VERIFY", {"error": "json parse"},
                                status="RED")
            return "RED"

    def step_shield_close(self) -> str:
        if self.dry_run:
            self.journal.append("SHIELD_CLOSE", {"dry_run": True})
            return "GREEN_DRY_RUN"
        rc, out = run_shield(["--close-session"])
        self.journal.append("SHIELD_CLOSE", {"rc": rc, "output": out[:500]},
                            status="OK" if rc == 0 else "WARN")
        return "GREEN" if rc == 0 else "YELLOW"

    def step_shield_purge(self) -> str:
        if self.dry_run:
            self.journal.append("SHIELD_PURGE", {"dry_run": True})
            return "GREEN_DRY_RUN"
        rc, out = run_shield(["--uninstall", "--purge"])
        ok = rc == 0 and "PURGE=OK" in out
        self.journal.append("SHIELD_PURGE", {"ok": ok, "output": out[:500]},
                            status="OK" if ok else "RED")
        return "GREEN" if ok else "RED"

    def step_post_fingerprint(self) -> str:
        rc, out = run_shield(["--fingerprint"], sudo=False)
        try:
            self.post_fingerprint = json.loads(out)
            fp = self.post_fingerprint
            self.journal.append("POST_FINGERPRINT", {"keys": len(fp) if fp else 0})
            return "GREEN"
        except json.JSONDecodeError:
            self.journal.append("POST_FINGERPRINT", {"error": "parse failed"},
                                status="RED")
            return "RED"

    def step_fingerprint_compare(self) -> str:
        if not self.pre_fingerprint or not self.post_fingerprint:
            return "RED:MISSING_FINGERPRINTS"
        diffs = []
        for key in set(list(self.pre_fingerprint.keys()) + list(self.post_fingerprint.keys())):
            if self.pre_fingerprint.get(key) != self.post_fingerprint.get(key):
                diffs.append(key)
        # Expected diffs: shield_files (purged), routes (transient)
        unexpected = [d for d in diffs if d not in ("shield_files", "routes")]
        ok = len(unexpected) == 0
        self.journal.append("FINGERPRINT_COMPARE", {
            "diffs": diffs, "unexpected": unexpected, "match": ok},
            status="OK" if ok else "RED")
        return "GREEN" if ok else f"RED:UNEXPECTED_DIFFS:{unexpected}"

    def _run_preflight(self) -> Dict[str, Any]:
        """Preflight-only: inspector + hash verify + esptool check.
        No serial, no flash, no shield, no fingerprint.
        Uses temp journal dir (/tmp/bootmux-preflight-*).
        """
        print("MODE=PREFLIGHT_ONLY (no serial, no flash)")
        self._setup_signal_handlers()

        # Use temp journal dir to avoid /var/db/ permission issues
        import tempfile
        temp_journal = Path(tempfile.mkdtemp(prefix="bootmux-preflight-"))
        self.journal = FlashJournal("preflight", temp_journal)
        self.journal.init()
        self.journal.append("PREFLIGHT_START", {"pid": os.getpid()})

        if not self.load_manifest():
            return {"status": "RED", "reason": "MANIFEST_MISSING"}

        results: Dict[str, str] = {}

        # Step 1: Bundle-local esptool availability
        bundle_dir = FIRMWARE_DIR.parent if FIRMWARE_DIR.exists() else None
        esptool_cmd = find_esptool(bundle_dir)
        if esptool_cmd:
            print(f"[BUNDLE_ESPTOOL] ... {' '.join(esptool_cmd)}")
            results["BUNDLE_ESPTOOL"] = "GREEN"
        else:
            print("[BUNDLE_ESPTOOL] ... RED (no esptool found)")
            results["BUNDLE_ESPTOOL"] = "RED"
            return {"status": "RED", "failed_step": "BUNDLE_ESPTOOL", "results": results}

        # Step 2: Hash re-verification from disk (independent of inspector)
        print("[HASH_VERIFY] ...", end=" ", flush=True)
        if not self.manifest or not self.build_dir:
            results["HASH_VERIFY"] = "RED:PRECONDITIONS"
            return {"status": "RED", "failed_step": "HASH_VERIFY", "results": results}
        hash_ok = True
        for art in self.manifest.get("artifacts", []):
            art_path = self.build_dir.parent / art["path"]
            if not art_path.exists():
                print(f"RED (missing {art['name']})")
                results["HASH_VERIFY"] = f"RED:MISSING:{art['name']}"
                hash_ok = False
                break
            actual = hashlib.sha256(art_path.read_bytes()).hexdigest()
            if actual != art["sha256"]:
                print(f"RED (hash mismatch {art['name']})")
                results["HASH_VERIFY"] = f"RED:HASH_MISMATCH:{art['name']}"
                hash_ok = False
                break
        if hash_ok:
            print("GREEN (all 3 artifacts match)")
            results["HASH_VERIFY"] = "GREEN"

        # Step 3: PRE_FLASH_GATE (inspector subprocess + hash re-verify)
        print("[PRE_FLASH_GATE] ...", end=" ", flush=True)
        gate_result = self.step_pre_flash_gate()
        results["PRE_FLASH_GATE"] = gate_result
        print(gate_result)

        # Step 4: Overall status
        if results.get("HASH_VERIFY", "").startswith("GREEN") and results.get("PRE_FLASH_GATE", "").startswith("GREEN"):
            overall = "GREEN"
        else:
            overall = "RED"

        return {"status": overall, "results": results, "preflight_only": True}

    def run(self) -> Dict[str, Any]:
        """Execute the full runner pipeline."""
        if self.preflight_only:
            return self._run_preflight()
        self._setup_signal_handlers()
        self.journal.init()
        self.journal.append("RUNNER_START", {
            "session_id": self.session_id, "dry_run": self.dry_run,
            "ttl": TTL_SECONDS, "pid": os.getpid(),
        })

        if not self.load_manifest():
            return {"status": "RED", "reason": "MANIFEST_MISSING"}

        steps = [
            ("PRE_FINGERPRINT", self.step_pre_fingerprint),
            ("SHIELD_INSTALL", self.step_shield_install),
            ("SHIELD_ARM", self.step_shield_arm),
            ("SERIAL_BASELINE", self.step_serial_baseline),
            ("SERIAL_DETECT", self.step_serial_detect),
            ("ROM_MODE_CHECK", self.step_rom_mode_check),
            ("PRE_FLASH_GATE", self.step_pre_flash_gate),
            ("FLASH", self.step_flash),
            ("FLASH_VERIFY", self.step_flash_verify),
            ("SAFE_IDENTITY_VERIFY", self.step_safe_identity_verify),
            ("SHIELD_CLOSE", self.step_shield_close),
            ("SHIELD_PURGE", self.step_shield_purge),
            ("POST_FINGERPRINT", self.step_post_fingerprint),
            ("FINGERPRINT_COMPARE", self.step_fingerprint_compare),
        ]

        results: Dict[str, str] = {}
        for name, fn in steps:
            if self._interrupted:
                break
            print(f"[{name}] ...", end=" ", flush=True)
            result = fn()
            results[name] = result
            print(result)
            if result.startswith("RED"):
                self.journal.append("RUNNER_ABORT", {"step": name, "result": result},
                                    status="RED")
                # Attempt rollback: close shield if armed
                if shield_is_armed():
                    print("[ROLLBACK] Closing shield...", flush=True)
                    self.step_shield_close()
                    self.step_shield_purge()
                return {"status": "RED", "failed_step": name, "results": results}

        self.journal.append("RUNNER_DONE", {"results": results})
        return {"status": "GREEN", "results": results}

    def resume(self) -> Dict[str, Any]:
        """Resume from journal after crash/interruption."""
        entries = self.journal.load()
        if not entries:
            return {"status": "RED", "reason": "NO_JOURNAL"}

        last = entries[-1]
        print(f"Resuming from journal: last event = {last.event}", file=sys.stderr)

        # Determine where to resume
        completed = {e.event for e in entries}
        if "RUNNER_DONE" in completed:
            return {"status": "GREEN", "reason": "ALREADY_DONE"}

        # If shield is still armed, close it first
        if shield_is_armed():
            print("[RESUME] Shield still armed — closing...", file=sys.stderr)
            self.step_shield_close()
            self.step_shield_purge()

        return {"status": "YELLOW", "reason": "RESUMED_AND_CLEANED",
                "last_event": last.event}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="BOOTMUX Safe Flash Runner")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Dry run (default in P4-R1)")
    parser.add_argument("--execute", action="store_true",
                        help="Actually execute (P4-R2 only)")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Preflight only: inspector + hash verify + esptool, no serial/flash")
    parser.add_argument("--resume", type=str, default=None,
                        help="Resume session by ID")
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument("--status", action="store_true",
                        help="Show runner status")
    args = parser.parse_args()

    if args.status:
        print("RUNNER_STATUS=READY_UNARMED")
        print("ATTACH_AUTHORITY=BLOCKED_PENDING_P4_R2")
        print(f"TTL_SECONDS={TTL_SECONDS}")
        print(f"MANIFEST={MANIFEST_PATH}")
        print(f"MANIFEST_EXISTS={MANIFEST_PATH.exists()}")
        esptool_cmd = find_esptool()
        print(f"ESPTOOL={'FOUND:' + esptool_cmd[0] if esptool_cmd else 'NOT_FOUND'}")
        return 0

    if args.resume:
        runner = SafeFlashRunner(session_id=args.resume, dry_run=not args.execute)
        result = runner.resume()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["status"] == "GREEN" else 1

    dry_run = not args.execute
    runner = SafeFlashRunner(session_id=args.session_id, dry_run=dry_run,
                             preflight_only=args.preflight_only)

    if dry_run and not args.preflight_only:
        print("MODE=DRY_RUN (P4-R1: execution deferred to P4-R2)")
        print("ATTACH_AUTHORITY=BLOCKED_PENDING_P4_R2")

    result = runner.run()
    print(f"\nRUNNER_RESULT={result['status']}")
    return 0 if result["status"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
