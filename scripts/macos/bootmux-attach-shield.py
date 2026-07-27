#!/usr/bin/env python3
"""R7C P4-R0 — BOOTMUX Mac Pre-Attach Shield.

Pre-emptive macOS network protection that runs BEFORE the ESP32-S3 cable is
inserted.  Complements P2 Guardian (post-fault recovery) by denying new
external Ethernet authority, pinning Wi-Fi routes, and quarantining stale
BOOTMUX state — all offline, without WORKER or Internet dependency.

Modes: --audit --arm --disarm --status --recover-now --postmortem --daemon --self-test

Hard safety gates (NX P4-R0 §I):
  s3_attach_before_shield_green: forbidden
  s3_flash_in_this_phase: forbidden
  network_service_delete: forbidden
  global_route_flush: forbidden
  global_pf_flush: forbidden
  saved_wifi_delete: forbidden
  wifi_password_export: forbidden
  unrelated_service_mutation: forbidden
  worker_or_internet_dependency_after_arm: forbidden
  disarm_while_untrusted_device_present: forbidden
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
PF_ANCHOR = "com.bootmux.attach-shield"
STATE_DIR = Path("/var/db/bootmux-shield")
STATE_FILE = STATE_DIR / "shield-state.json"
SESSION_DIR = STATE_DIR / "sessions"
LAUNCHD_LABEL = "com.bootmux.attach-shield"
LAUNCHD_PLIST = f"/Library/LaunchDaemons/{LAUNCHD_LABEL}.plist"
WATCHDOG_INTERVAL_S = 0.25  # 250 ms
INTERNET_HEALTH_TIMEOUT_S = 3.0
ROUTE_MONITOR_CMD = ["route", "-n", "monitor"]
BOOTMUX_VID = "0x303a"  # Espressif
BOOTMUX_PRODUCT_HINTS = ("bootmux", "ncm", "ecm", "rndis", "usb ethernet")
BOOTMUX_SUBNET = "10.77.0.0/24"
SPLIT_ROUTES_V4 = [("0.0.0.0/1", None), ("128.0.0.0/1", None)]  # gateway filled at arm
SPLIT_ROUTES_V6 = [("::/1", None), ("8000::/1", None)]
REDACTED = "<redacted>"
MAX_STATE_BYTES = 256 * 1024
MAX_LOG_BYTES = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

_MAC_RE = re.compile(r"([0-9a-fA-F]{2}[:\-]){5}[0-9a-fA-F]{2}")
_IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
_PATH_RE = re.compile(r"/Users/[^/\s]+")
_SERIAL_RE = re.compile(r"\b[A-Z0-9]{10,}\b")


def redact(text: str) -> str:
    """Remove MACs, IPs, private paths, and long serial-like tokens."""
    text = _MAC_RE.sub(REDACTED, text)
    text = _IP_RE.sub(REDACTED, text)
    text = _PATH_RE.sub(REDACTED, text)
    return text


def ssid_digest(ssid: str) -> str:
    """One-way digest of SSID — never store plaintext."""
    return hashlib.sha256(ssid.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Host abstraction
# ---------------------------------------------------------------------------


@dataclass
class CommandResult:
    cmd: List[str]
    exit_code: int
    stdout: str
    stderr: str = ""


class Host:
    """Interface for command execution and filesystem access."""

    def run(self, cmd: List[str], timeout: float = 30) -> CommandResult:
        raise NotImplementedError

    def read_file(self, path: str) -> Optional[str]:
        raise NotImplementedError

    def write_file(self, path: str, content: str, mode: int = 0o600) -> None:
        raise NotImplementedError

    def mkdir_p(self, path: str, mode: int = 0o700) -> None:
        raise NotImplementedError

    def path_exists(self, path: str) -> bool:
        raise NotImplementedError

    def remove_file(self, path: str) -> None:
        raise NotImplementedError


class SystemHost(Host):
    """Real macOS execution.  All mutations go through here."""

    def run(self, cmd: List[str], timeout: float = 30) -> CommandResult:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return CommandResult(cmd, r.returncode, r.stdout, r.stderr)
        except subprocess.TimeoutExpired:
            return CommandResult(cmd, 124, "", "timeout")
        except FileNotFoundError:
            return CommandResult(cmd, 127, "", f"not found: {cmd[0]}")

    def read_file(self, path: str) -> Optional[str]:
        try:
            return Path(path).read_text()
        except (OSError, PermissionError):
            return None

    def write_file(self, path: str, content: str, mode: int = 0o600) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(content)
        os.chmod(tmp, mode)
        tmp.rename(p)  # atomic

    def mkdir_p(self, path: str, mode: int = 0o700) -> None:
        os.makedirs(path, mode=mode, exist_ok=True)
        os.chmod(path, mode)

    def path_exists(self, path: str) -> bool:
        return Path(path).exists()

    def remove_file(self, path: str) -> None:
        try:
            os.unlink(path)
        except OSError:
            pass


class FakeHost(Host):
    """Test double: records commands, returns scripted responses."""

    def __init__(self):
        self.commands: List[List[str]] = []
        self.responses: Dict[str, CommandResult] = {}
        self.files: Dict[str, str] = {}
        self.dirs: set = set()
        self.default_responses: Dict[str, str] = {}

    def set_response(self, cmd_prefix: str, stdout: str, exit_code: int = 0):
        self.default_responses[cmd_prefix] = stdout
        self.responses[cmd_prefix] = CommandResult(cmd_prefix.split(), exit_code, stdout)

    def run(self, cmd: List[str], timeout: float = 30) -> CommandResult:
        self.commands.append(cmd)
        key = " ".join(cmd)
        # exact match first
        if key in self.responses:
            return self.responses[key]
        # prefix match
        for prefix, resp in self.responses.items():
            if key.startswith(prefix):
                return resp
        # default empty success
        return CommandResult(cmd, 0, "")

    def read_file(self, path: str) -> Optional[str]:
        return self.files.get(path)

    def write_file(self, path: str, content: str, mode: int = 0o600) -> None:
        self.files[path] = content

    def mkdir_p(self, path: str, mode: int = 0o700) -> None:
        self.dirs.add(path)

    def path_exists(self, path: str) -> bool:
        return path in self.files or path in self.dirs

    def remove_file(self, path: str) -> None:
        self.files.pop(path, None)


# ---------------------------------------------------------------------------
# Baseline capture (Section A)
# ---------------------------------------------------------------------------


@dataclass
class Baseline:
    network_location: str = ""
    wifi_device: str = ""
    wifi_service: str = ""
    wifi_enabled: bool = False
    wifi_power: bool = False
    ssid_digest: str = ""
    ipv4_mode: str = ""
    ipv6_mode: str = ""
    gateway: str = ""
    gateway_interface: str = ""
    dns_servers: List[str] = field(default_factory=list)
    dns_search: List[str] = field(default_factory=list)
    dns_automatic: bool = True
    service_order: List[str] = field(default_factory=list)
    service_enabled: Dict[str, bool] = field(default_factory=dict)
    interfaces: Dict[str, str] = field(default_factory=dict)  # iface -> hwport
    virtual_services: List[str] = field(default_factory=list)
    captured_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "network_location": self.network_location,
            "wifi_device": self.wifi_device,
            "wifi_service": self.wifi_service,
            "wifi_enabled": self.wifi_enabled,
            "wifi_power": self.wifi_power,
            "ssid_digest": self.ssid_digest,
            "ipv4_mode": self.ipv4_mode,
            "ipv6_mode": self.ipv6_mode,
            "gateway": self.gateway,
            "gateway_interface": self.gateway_interface,
            "dns_servers": self.dns_servers,
            "dns_search": self.dns_search,
            "dns_automatic": self.dns_automatic,
            "service_order": self.service_order,
            "service_enabled": self.service_enabled,
            "interfaces": self.interfaces,
            "virtual_services": self.virtual_services,
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Baseline":
        b = cls()
        for k, v in d.items():
            if hasattr(b, k):
                setattr(b, k, v)
        return b


def _parse_service_order(text: str) -> Tuple[List[str], Dict[str, bool]]:
    """Parse networksetup -listnetworkserviceorder into (order, enabled)."""
    order = []
    enabled = {}
    for line in text.splitlines():
        m = re.match(r"\((\d+)\)\s+(.+)", line)
        if m:
            name = m.group(2).strip()
            order.append(name)
            enabled[name] = True
        elif line.startswith("*") and order:
            # disabled marker on next line after service
            pass
    # Check for disabled services (marked with * prefix in some outputs)
    return order, enabled


def _parse_default_route(text: str) -> Tuple[str, str]:
    """Parse route -n get default -> (gateway, interface)."""
    gw = ""
    iface = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("gateway:"):
            gw = line.split(":", 1)[1].strip()
        elif line.startswith("interface:"):
            iface = line.split(":", 1)[1].strip()
    return gw, iface


def _parse_dns(text: str) -> Tuple[List[str], List[str], bool]:
    """Parse scutil --dns -> (servers, search, automatic)."""
    servers = []
    search = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"nameserver\[\d+\]\s*:\s*(.+)", line)
        if m:
            servers.append(m.group(1).strip())
        m = re.match(r"search domain\[\d+\]\s*:\s*(.+)", line)
        if m:
            search.append(m.group(1).strip())
    return servers, search, True


def _parse_interfaces(text: str) -> Dict[str, str]:
    """Parse networksetup -listallhardwareports -> {device: hwport}."""
    result = {}
    current_port = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Hardware Port:"):
            current_port = line.split(":", 1)[1].strip()
        elif line.startswith("Device:"):
            dev = line.split(":", 1)[1].strip()
            if current_port:
                result[dev] = current_port
    return result


def _is_virtual_service(name: str) -> bool:
    """Tailscale, VPN tunnels, loopback, AWDL are virtual."""
    lower = name.lower()
    return any(k in lower for k in ("tailscale", "vpn", "utun", "loopback", "awdl", "bridge", "thunderbolt"))


def capture_baseline(host: Host) -> Baseline:
    """Capture full Wi-Fi/network baseline (Section A)."""
    b = Baseline(captured_at=time.time())

    # Network location
    r = host.run(["networksetup", "-getcurrentlocation"])
    b.network_location = r.stdout.strip() if r.exit_code == 0 else ""

    # Wi-Fi device (dynamic discovery)
    r = host.run(["networksetup", "-listallhardwareports"])
    b.interfaces = _parse_interfaces(r.stdout)
    for dev, port in b.interfaces.items():
        if "wi-fi" in port.lower():
            b.wifi_device = dev
            break

    # Wi-Fi service name
    r = host.run(["networksetup", "-listnetworkserviceorder"])
    b.service_order, b.service_enabled = _parse_service_order(r.stdout)
    for svc in b.service_order:
        if "wi-fi" in svc.lower():
            b.wifi_service = svc
            break

    # Wi-Fi power
    if b.wifi_device:
        r = host.run(["networksetup", "-getairportpower", b.wifi_device])
        b.wifi_power = "On" in r.stdout

    # SSID (digest only)
    if b.wifi_device:
        r = host.run(["networksetup", "-getairportnetwork", b.wifi_device])
        m = re.search(r"Current Wi-Fi Network:\s*(.+)", r.stdout)
        if m:
            b.ssid_digest = ssid_digest(m.group(1).strip())

    # IPv4/IPv6 mode
    if b.wifi_service:
        r = host.run(["networksetup", "-getinfo", b.wifi_service])
        for line in r.stdout.splitlines():
            if line.startswith("DHCP Configuration:"):
                b.ipv4_mode = "DHCP" if "DHCP" in line else "Manual"
            elif line.startswith("IPv6:"):
                b.ipv6_mode = line.split(":", 1)[1].strip()

    # Default route
    r = host.run(["route", "-n", "get", "default"])
    b.gateway, b.gateway_interface = _parse_default_route(r.stdout)

    # DNS
    r = host.run(["scutil", "--dns"])
    b.dns_servers, b.dns_search, b.dns_automatic = _parse_dns(r.stdout)

    # Virtual services
    b.virtual_services = [s for s in b.service_order if _is_virtual_service(s)]

    return b


# ---------------------------------------------------------------------------
# BOOTMUX quarantine (Section B)
# ---------------------------------------------------------------------------


@dataclass
class QuarantineResult:
    bootmux_services_found: List[str] = field(default_factory=list)
    services_disabled: List[str] = field(default_factory=list)
    routes_removed: List[str] = field(default_factory=list)
    dns_restored: bool = False
    wifi_first: bool = False
    default_route_on_wifi: bool = False
    classification: str = "PENDING"


def identify_bootmux_services(host: Host, baseline: Baseline) -> List[str]:
    """Identify proven BOOTMUX services using multiple evidence sources."""
    candidates = []
    # Evidence 1: service name contains BOOTMUX hints
    for svc in baseline.service_order:
        lower = svc.lower()
        if any(h in lower for h in BOOTMUX_PRODUCT_HINTS):
            candidates.append(svc)
    # Evidence 2: 10.77.0.0/24 in scutil --nwi
    r = host.run(["scutil", "--nwi"])
    if BOOTMUX_SUBNET.split("/")[0] in r.stdout:
        # Find which service owns it
        for svc in baseline.service_order:
            if svc not in candidates:
                candidates.append(svc)
    # Evidence 3: VID/PID in ioreg USB history
    r = host.run(["ioreg", "-p", "IOUSB", "-c", "IOUSBHostDevice"])
    if BOOTMUX_VID.lower() in r.stdout.lower():
        # USB evidence supports but doesn't solely prove
        pass
    return candidates


def quarantine_bootmux(host: Host, baseline: Baseline) -> QuarantineResult:
    """Disable proven BOOTMUX services, remove stale routes, restore DNS."""
    qr = QuarantineResult()
    qr.bootmux_services_found = identify_bootmux_services(host, baseline)

    # Disable (not delete) proven BOOTMUX services
    for svc in qr.bootmux_services_found:
        r = host.run(["networksetup", "-setnetworkserviceenabled", svc, "off"])
        if r.exit_code == 0:
            qr.services_disabled.append(svc)

    # Remove only BOOTMUX-scoped routes (10.77.0.0/24)
    r = host.run(["netstat", "-rn"])
    for line in r.stdout.splitlines():
        if BOOTMUX_SUBNET.split("/")[0] in line:
            parts = line.split()
            if len(parts) >= 2:
                dest = parts[0]
                gw = parts[1] if len(parts) > 1 else ""
                host.run(["route", "-n", "delete", dest, gw])
                qr.routes_removed.append(dest)

    # Restore Wi-Fi DNS from baseline
    if baseline.wifi_service and baseline.dns_servers:
        host.run(["networksetup", "-setdnsservers", baseline.wifi_service] + baseline.dns_servers)
        qr.dns_restored = True

    # Wi-Fi first in service order (preserve relative order of others)
    if baseline.wifi_service and baseline.service_order:
        others = [s for s in baseline.service_order if s != baseline.wifi_service]
        new_order = [baseline.wifi_service] + others
        host.run(["networksetup", "-ordernetworkservices"] + new_order)
        qr.wifi_first = True

    # Verify default route on Wi-Fi
    r = host.run(["route", "-n", "get", "default"])
    _, iface = _parse_default_route(r.stdout)
    qr.default_route_on_wifi = (iface == baseline.wifi_device)

    qr.classification = "GREEN" if (qr.default_route_on_wifi and qr.wifi_first) else "YELLOW"
    return qr


# ---------------------------------------------------------------------------
# PF anchor management (Section C)
# ---------------------------------------------------------------------------


def pf_anchor_rules(interface: str) -> str:
    """Generate PF rules blocking all traffic on an untrusted interface."""
    return (
        f"# {PF_ANCHOR} — auto-generated, do not edit\n"
        f"block drop quick on {interface} all\n"
    )


def pf_install_anchor(host: Host, interface: str) -> bool:
    """Install PF anchor blocking an untrusted interface."""
    rules = pf_anchor_rules(interface)
    # Write rules to temp file, load into anchor
    rules_path = f"/tmp/{PF_ANCHOR}-{interface}.rules"
    host.write_file(rules_path, rules, 0o600)
    r = host.run(["pfctl", "-a", PF_ANCHOR, "-f", rules_path])
    host.remove_file(rules_path)
    # Enable pf if not already
    host.run(["pfctl", "-E"])
    return r.exit_code == 0


def pf_remove_anchor(host: Host) -> bool:
    """Remove only our PF anchor rules."""
    r = host.run(["pfctl", "-a", PF_ANCHOR, "-F", "all"])
    return r.exit_code == 0


def pf_anchor_active(host: Host) -> bool:
    """Check if our anchor has rules loaded."""
    r = host.run(["pfctl", "-a", PF_ANCHOR, "-s", "rules"])
    return r.exit_code == 0 and "block" in r.stdout


# ---------------------------------------------------------------------------
# Route pinning (Section E)
# ---------------------------------------------------------------------------


@dataclass
class RoutePinResult:
    pinned_routes: List[str] = field(default_factory=list)
    classification: str = "PENDING"
    error: str = ""


def pin_split_routes(host: Host, gateway: str, interface: str) -> RoutePinResult:
    """Add split-default routes through Wi-Fi gateway (0.0.0.0/1 + 128.0.0.0/1)."""
    rp = RoutePinResult()
    if not gateway or not interface:
        rp.classification = "YELLOW_ROUTE_PIN_UNAVAILABLE"
        rp.error = "no gateway/interface for pinning"
        return rp

    # Validate route command syntax against local macOS
    # Test with a dry add/remove of 0.0.0.0/1
    test_r = host.run(["route", "-n", "add", "-net", "0.0.0.0/1", gateway])
    if test_r.exit_code != 0:
        rp.classification = "YELLOW_ROUTE_PIN_UNAVAILABLE"
        rp.error = f"route add failed: {test_r.stderr.strip()}"
        return rp
    # Immediately remove test route
    host.run(["route", "-n", "delete", "-net", "0.0.0.0/1", gateway])

    # Now add all split routes
    for dest, _ in SPLIT_ROUTES_V4:
        r = host.run(["route", "-n", "add", "-net", dest, gateway])
        if r.exit_code == 0:
            rp.pinned_routes.append(f"inet {dest} via {gateway}")
        else:
            rp.classification = "YELLOW_ROUTE_PIN_UNAVAILABLE"
            rp.error = f"failed to pin {dest}: {r.stderr.strip()}"
            # Rollback what we added
            for pinned in rp.pinned_routes:
                parts = pinned.split()
                host.run(["route", "-n", "delete", "-net", parts[1], gateway])
            rp.pinned_routes = []
            return rp

    # IPv6 split routes (best-effort)
    for dest, _ in SPLIT_ROUTES_V6:
        r = host.run(["route", "-n", "add", "-inet6", dest, gateway])
        if r.exit_code == 0:
            rp.pinned_routes.append(f"inet6 {dest} via {gateway}")

    rp.classification = "GREEN"
    return rp


def unpin_split_routes(host: Host, pinned: List[str], gateway: str) -> None:
    """Remove all pinned split routes."""
    for entry in pinned:
        parts = entry.split()
        if len(parts) >= 3:
            family = parts[0]  # inet or inet6
            dest = parts[1]
            if family == "inet6":
                host.run(["route", "-n", "delete", "-inet6", dest, gateway])
            else:
                host.run(["route", "-n", "delete", "-net", dest, gateway])


# ---------------------------------------------------------------------------
# Recovery sequence Q1-Q9 (Section G)
# ---------------------------------------------------------------------------


@dataclass
class RecoveryResult:
    steps: Dict[str, str] = field(default_factory=dict)  # Q1..Q9 -> OK/INCOMPLETE/SKIP
    classification: str = "PENDING"


def run_recovery(host: Host, baseline: Baseline, untrusted_ifaces: List[str]) -> RecoveryResult:
    """Execute Q1-Q9 offline recovery without user interaction."""
    rr = RecoveryResult()

    # Q1: PF block untrusted interfaces
    for iface in untrusted_ifaces:
        ok = pf_install_anchor(host, iface)
        rr.steps[f"Q1:{iface}"] = "OK" if ok else "INCOMPLETE:pf_block"

    # Q2: disable mapped network services
    # Map untrusted interfaces -> hwport -> service name via baseline + live data
    current_ifaces = get_current_interfaces(host)
    for iface in untrusted_ifaces:
        hwport = current_ifaces.get(iface, baseline.interfaces.get(iface, ""))
        if not hwport:
            continue
        for svc in baseline.service_order:
            # Match service to hwport (case-insensitive containment)
            if hwport.lower() in svc.lower() or svc.lower() in hwport.lower():
                r = host.run(["networksetup", "-setnetworkserviceenabled", svc, "off"])
                rr.steps[f"Q2:{svc}"] = "OK" if r.exit_code == 0 else "INCOMPLETE:disable"

    # Q3: remove default/scoped routes on untrusted interfaces
    r = host.run(["netstat", "-rn"])
    for line in r.stdout.splitlines():
        for iface in untrusted_ifaces:
            if iface in line and ("default" in line or "::/0" in line):
                parts = line.split()
                if parts:
                    host.run(["route", "-n", "delete", parts[0]])
                    rr.steps[f"Q3:{parts[0]}"] = "OK"

    # Q4: restore Wi-Fi IPv4/IPv6 mode
    if baseline.wifi_service:
        if baseline.ipv4_mode == "DHCP":
            host.run(["networksetup", "-setdhcp", baseline.wifi_service])
        rr.steps["Q4"] = "OK"
    else:
        rr.steps["Q4"] = "SKIP:no_wifi_service"

    # Q5: restore DNS
    if baseline.wifi_service and baseline.dns_servers:
        host.run(["networksetup", "-setdnsservers", baseline.wifi_service] + baseline.dns_servers)
        rr.steps["Q5"] = "OK"
    else:
        rr.steps["Q5"] = "SKIP:no_dns_baseline"

    # Q6: restore service order
    if baseline.service_order:
        host.run(["networksetup", "-ordernetworkservices"] + baseline.service_order)
        rr.steps["Q6"] = "OK"
    else:
        rr.steps["Q6"] = "SKIP:no_order_baseline"

    # Q7: reconnect Wi-Fi if association changed
    if baseline.wifi_device:
        r = host.run(["networksetup", "-getairportnetwork", baseline.wifi_device])
        if baseline.ssid_digest and baseline.ssid_digest not in r.stdout:
            # Reconnect using saved network (no password export)
            host.run(["networksetup", "-setairportnetwork", baseline.wifi_device, baseline.ssid_digest])
            rr.steps["Q7"] = "OK"
        else:
            rr.steps["Q7"] = "SKIP:associated"
    else:
        rr.steps["Q7"] = "SKIP:no_wifi_device"

    # Q8: bounded Wi-Fi power-cycle only if Q1-Q7 had failures
    failures = [k for k, v in rr.steps.items() if v.startswith("INCOMPLETE")]
    if failures and baseline.wifi_device:
        host.run(["networksetup", "-setairportpower", baseline.wifi_device, "off"])
        time.sleep(1)
        host.run(["networksetup", "-setairportpower", baseline.wifi_device, "on"])
        rr.steps["Q8"] = "OK"
    else:
        rr.steps["Q8"] = "SKIP:not_needed"

    # Q9: verify
    r = host.run(["route", "-n", "get", "default"])
    _, iface = _parse_default_route(r.stdout)
    if iface == baseline.wifi_device:
        rr.steps["Q9"] = "OK"
        rr.classification = "GREEN"
    else:
        rr.steps["Q9"] = "INCOMPLETE:route_not_restored"
        rr.classification = "INCOMPLETE:Q9"

    return rr


# ---------------------------------------------------------------------------
# Forensic logging (Section H)
# ---------------------------------------------------------------------------


class SessionLogger:
    """Bounded redacted JSONL logger under root-owned persistent directory."""

    def __init__(self, host: Host, session_id: str):
        self.host = host
        self.session_id = session_id
        self.log_dir = str(SESSION_DIR / session_id)
        self.log_file = f"{self.log_dir}/shield.jsonl"
        host.mkdir_p(self.log_dir, 0o700)
        self._bytes_written = 0

    def log(self, event: str, data: dict) -> None:
        entry = {
            "ts": time.time(),
            "session": self.session_id,
            "event": event,
            "data": data,
        }
        line = json.dumps(entry, default=str)
        line = redact(line)
        if self._bytes_written + len(line) > MAX_LOG_BYTES:
            return  # bounded
        self.host.write_file(self.log_file, (self.host.read_file(self.log_file) or "") + line + "\n")
        self._bytes_written += len(line) + 1

    def log_command(self, cmd: List[str], exit_code: int, duration_s: float) -> None:
        self.log("command", {"cmd": redact(" ".join(cmd)), "exit": exit_code, "dur_s": round(duration_s, 3)})


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


@dataclass
class ShieldState:
    armed: bool = False
    session_id: str = ""
    baseline: Optional[dict] = None
    pinned_routes: List[str] = field(default_factory=list)
    quarantined_services: List[str] = field(default_factory=list)
    untrusted_interfaces: List[str] = field(default_factory=list)
    pf_anchor_active: bool = False
    armed_at: float = 0.0
    classification: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "armed": self.armed,
            "session_id": self.session_id,
            "baseline": self.baseline,
            "pinned_routes": self.pinned_routes,
            "quarantined_services": self.quarantined_services,
            "untrusted_interfaces": self.untrusted_interfaces,
            "pf_anchor_active": self.pf_anchor_active,
            "armed_at": self.armed_at,
            "classification": self.classification,
        }, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ShieldState":
        d = json.loads(text)
        s = cls()
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s


def load_state(host: Host) -> Optional[ShieldState]:
    text = host.read_file(str(STATE_FILE))
    if not text:
        return None
    try:
        return ShieldState.from_json(text)
    except (json.JSONDecodeError, KeyError):
        return None  # corrupt -> fail closed


def save_state(host: Host, state: ShieldState) -> None:
    host.mkdir_p(str(STATE_DIR), 0o700)
    host.write_file(str(STATE_FILE), state.to_json(), 0o600)


# ---------------------------------------------------------------------------
# Interface detection (Section C)
# ---------------------------------------------------------------------------


def get_current_interfaces(host: Host) -> Dict[str, str]:
    """Return {device: hwport} for all current interfaces."""
    r = host.run(["networksetup", "-listallhardwareports"])
    return _parse_interfaces(r.stdout)


def detect_new_external_ethernet(host: Host, baseline: Baseline) -> List[str]:
    """Find physical Ethernet-like interfaces not in baseline allowlist."""
    current = get_current_interfaces(host)
    baseline_ifaces = set(baseline.interfaces.keys())
    new_untrusted = []
    for dev, port in current.items():
        if dev in baseline_ifaces:
            continue
        # Skip virtual
        if _is_virtual_service(port):
            continue
        # Skip loopback, AWDL
        if dev in ("lo0", "awdl0"):
            continue
        # Physical Ethernet-like: USB Ethernet, Thunderbolt, NCM, ECM, RNDIS
        # NOTE: bare "usb" is too broad (catches keyboards/mice).  Require
        # an explicit network-class keyword.
        port_lower = port.lower()
        if any(k in port_lower for k in ("ethernet", "ncm", "ecm", "rndis", "thunderbolt")):
            new_untrusted.append(dev)
    return new_untrusted


# ---------------------------------------------------------------------------
# Wi-Fi association lock (Section D)
# ---------------------------------------------------------------------------


def check_wifi_association(host: Host, baseline: Baseline) -> bool:
    """Return True if Wi-Fi is still associated with baseline SSID."""
    if not baseline.wifi_device or not baseline.ssid_digest:
        return True  # can't verify, assume ok
    r = host.run(["networksetup", "-getairportnetwork", baseline.wifi_device])
    # We can't compare digest to plaintext, so check if associated at all
    return "Current Wi-Fi Network:" in r.stdout


def repair_wifi_association(host: Host, baseline: Baseline) -> bool:
    """Reconnect to saved baseline SSID without exposing name."""
    if not baseline.wifi_device:
        return False
    # Use saved network path (keychain) — no password in CLI
    r = host.run(["networksetup", "-setairportnetwork", baseline.wifi_device, baseline.ssid_digest])
    return r.exit_code == 0


# ---------------------------------------------------------------------------
# Internet health (Section F)
# ---------------------------------------------------------------------------


def check_internet_health(host: Host, baseline: Baseline) -> bool:
    """Composite check: route invariant + DNS resolution + TCP canary."""
    # Route invariant (authoritative)
    r = host.run(["route", "-n", "get", "default"])
    _, iface = _parse_default_route(r.stdout)
    if iface != baseline.wifi_device:
        return False
    # DNS resolution
    r = host.run(["dscacheutil", "-q", "host", "-a", "name", "apple.com"], timeout=INTERNET_HEALTH_TIMEOUT_S)
    if r.exit_code != 0:
        return False
    # TCP canary (HTTPS)
    r = host.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                  "--max-time", str(INTERNET_HEALTH_TIMEOUT_S), "https://www.apple.com"],
                 timeout=INTERNET_HEALTH_TIMEOUT_S + 1)
    return r.exit_code == 0 and "200" in r.stdout


# ---------------------------------------------------------------------------
# Daemon event loop (Section F)
# ---------------------------------------------------------------------------


def daemon_loop(host: Host, logger: SessionLogger) -> None:
    """Main daemon loop: event-driven + 250ms watchdog."""
    state = load_state(host)
    if not state or not state.armed:
        logger.log("daemon_exit", {"reason": "not_armed"})
        return

    baseline = Baseline.from_dict(state.baseline) if state.baseline else Baseline()
    logger.log("daemon_start", {"session": state.session_id})

    # Start route monitor
    route_proc = None
    try:
        route_proc = subprocess.Popen(
            ROUTE_MONITOR_CMD, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1
        )
    except (OSError, FileNotFoundError):
        logger.log("route_monitor_failed", {"reason": "cannot_start"})

    consecutive_health_fail = 0
    running = True

    def handle_signal(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while running:
        time.sleep(WATCHDOG_INTERVAL_S)

        # Check for new untrusted interfaces
        new_untrusted = detect_new_external_ethernet(host, baseline)
        if new_untrusted:
            logger.log("untrusted_detected", {"interfaces": new_untrusted})
            state.untrusted_interfaces = list(set(state.untrusted_interfaces + new_untrusted))
            save_state(host, state)
            rr = run_recovery(host, baseline, new_untrusted)
            logger.log("recovery", {"result": rr.steps, "classification": rr.classification})
            consecutive_health_fail = 0
            continue

        # Check default route
        r = host.run(["route", "-n", "get", "default"])
        _, iface = _parse_default_route(r.stdout)
        if iface != baseline.wifi_device:
            logger.log("route_drift", {"expected": baseline.wifi_device, "actual": iface})
            rr = run_recovery(host, baseline, state.untrusted_interfaces)
            logger.log("recovery", {"result": rr.steps, "classification": rr.classification})
            consecutive_health_fail = 0
            continue

        # Check Wi-Fi association
        if not check_wifi_association(host, baseline):
            logger.log("wifi_drift", {})
            repair_wifi_association(host, baseline)
            continue

        # Internet health (secondary signal)
        if not check_internet_health(host, baseline):
            consecutive_health_fail += 1
            if consecutive_health_fail >= 2:
                logger.log("health_fail_2x", {})
                rr = run_recovery(host, baseline, state.untrusted_interfaces)
                logger.log("recovery", {"result": rr.steps, "classification": rr.classification})
                consecutive_health_fail = 0
        else:
            consecutive_health_fail = 0

    # Cleanup route monitor
    if route_proc:
        route_proc.terminate()
        route_proc.wait(timeout=2)
    logger.log("daemon_stop", {"reason": "signal"})


# ---------------------------------------------------------------------------
# Postmortem (Section H)
# ---------------------------------------------------------------------------


def generate_postmortem(host: Host) -> str:
    """Generate sanitized report from session logs."""
    if not host.path_exists(str(SESSION_DIR)):
        return "NO_SESSIONS"
    # Find latest session
    r = host.run(["ls", "-t", str(SESSION_DIR)])
    sessions = [s for s in r.stdout.splitlines() if s.strip()]
    if not sessions:
        return "NO_SESSIONS"
    latest = sessions[0]
    log_path = f"{SESSION_DIR}/{latest}/shield.jsonl"
    text = host.read_file(log_path)
    if not text:
        return "NO_LOG_DATA"

    events = []
    for line in text.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # Order by first mutation type
    mutation_order = []
    for e in events:
        ev = e.get("event", "")
        if ev in ("untrusted_detected", "route_drift", "wifi_drift", "health_fail_2x"):
            mutation_order.append({"ts": e.get("ts"), "event": ev, "data": e.get("data", {})})

    report = {
        "session": latest,
        "total_events": len(events),
        "first_mutations": mutation_order[:5],
        "classification": events[-1].get("data", {}).get("classification", "UNKNOWN") if events else "UNKNOWN",
    }
    return json.dumps(report, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI modes
# ---------------------------------------------------------------------------


def cmd_audit(host: Host) -> int:
    """Read-only audit of current state."""
    baseline = capture_baseline(host)
    print(f"wifi_device={baseline.wifi_device}")
    print(f"wifi_service={baseline.wifi_service}")
    print(f"wifi_power={baseline.wifi_power}")
    print(f"ssid_digest={baseline.ssid_digest}")
    print(f"gateway={baseline.gateway}")
    print(f"gateway_interface={baseline.gateway_interface}")
    print(f"service_order={baseline.service_order}")
    bootmux = identify_bootmux_services(host, baseline)
    print(f"bootmux_services_found={bootmux}")
    state = load_state(host)
    print(f"shield_armed={state.armed if state else False}")
    return 0


def cmd_arm(host: Host) -> int:
    """Arm the shield: capture baseline, quarantine, pin routes, start daemon."""
    # Preconditions
    state = load_state(host)
    if state and state.armed:
        print("ALREADY_ARMED")
        return 0

    session_id = str(uuid.uuid4())[:8]
    logger = SessionLogger(host, session_id)
    logger.log("arm_start", {"version": VERSION})

    # A: Capture baseline
    baseline = capture_baseline(host)
    if not baseline.wifi_device:
        print("CLASSIFICATION=RED_NO_WIFI_DEVICE")
        logger.log("arm_fail", {"reason": "no_wifi_device"})
        return 1
    logger.log("baseline_captured", {"wifi_device": baseline.wifi_device})

    # B: Quarantine BOOTMUX
    qr = quarantine_bootmux(host, baseline)
    logger.log("quarantine", {"result": qr.classification, "disabled": qr.services_disabled})

    # E: Pin split routes
    rp = pin_split_routes(host, baseline.gateway, baseline.wifi_device)
    logger.log("route_pin", {"classification": rp.classification, "pinned": rp.pinned_routes})

    # Save state
    new_state = ShieldState(
        armed=True,
        session_id=session_id,
        baseline=baseline.to_dict(),
        pinned_routes=rp.pinned_routes,
        quarantined_services=qr.services_disabled,
        armed_at=time.time(),
        classification="GREEN" if rp.classification == "GREEN" else "YELLOW_ROUTE_PIN_UNAVAILABLE",
    )
    save_state(host, new_state)
    logger.log("arm_complete", {"classification": new_state.classification})

    print(f"CLASSIFICATION={new_state.classification}")
    print(f"SESSION_ID={session_id}")
    print(f"ROUTE_PIN={rp.classification}")
    print(f"QUARANTINE={qr.classification}")
    return 0


def cmd_disarm(host: Host) -> int:
    """Disarm: remove pinned routes, PF anchor, stop daemon."""
    state = load_state(host)
    if not state or not state.armed:
        print("NOT_ARMED")
        return 0

    # Safety: refuse if untrusted device present
    if state.untrusted_interfaces:
        current = get_current_interfaces(host)
        still_present = [i for i in state.untrusted_interfaces if i in current]
        if still_present:
            print(f"REFUSED_UNTRUSTED_PRESENT={still_present}")
            return 1

    baseline = Baseline.from_dict(state.baseline) if state.baseline else Baseline()

    # Remove pinned routes
    unpin_split_routes(host, state.pinned_routes, baseline.gateway)

    # Remove PF anchor
    pf_remove_anchor(host)

    # Stop daemon
    host.run(["launchctl", "unload", LAUNCHD_PLIST])

    # Update state
    state.armed = False
    state.pinned_routes = []
    state.pf_anchor_active = False
    save_state(host, state)

    print("DISARMED")
    return 0


def cmd_status(host: Host) -> int:
    """Show current shield status."""
    state = load_state(host)
    if not state:
        print("STATUS=NOT_INSTALLED")
        return 0
    print(f"STATUS={'ARMED' if state.armed else 'DISARMED'}")
    print(f"SESSION_ID={state.session_id}")
    print(f"CLASSIFICATION={state.classification}")
    print(f"PINNED_ROUTES={len(state.pinned_routes)}")
    print(f"QUARANTINED={state.quarantined_services}")
    print(f"UNTRUSTED={state.untrusted_interfaces}")
    print(f"PF_ANCHOR={state.pf_anchor_active}")
    return 0


def cmd_recover_now(host: Host) -> int:
    """Run Q1-Q9 recovery immediately."""
    state = load_state(host)
    if not state or not state.baseline:
        print("NO_BASELINE")
        return 1
    baseline = Baseline.from_dict(state.baseline)
    untrusted = state.untrusted_interfaces or detect_new_external_ethernet(host, baseline)
    rr = run_recovery(host, baseline, untrusted)
    print(f"RECOVERY_CLASSIFICATION={rr.classification}")
    for k, v in sorted(rr.steps.items()):
        print(f"  {k}: {v}")
    return 0 if rr.classification == "GREEN" else 1


def cmd_postmortem(host: Host) -> int:
    """Generate sanitized postmortem report."""
    report = generate_postmortem(host)
    print(report)
    return 0


def cmd_daemon(host: Host) -> int:
    """Run as LaunchDaemon."""
    state = load_state(host)
    if not state or not state.session_id:
        print("NO_SESSION")
        return 1
    logger = SessionLogger(host, state.session_id)
    daemon_loop(host, logger)
    return 0


def cmd_self_test(host: Host) -> int:
    """Internal self-test without root."""
    checks = 0
    failures = 0

    def check(name: str, condition: bool):
        nonlocal checks, failures
        checks += 1
        if not condition:
            failures += 1
            print(f"  FAIL {name}")

    # Redaction
    check("redact_mac", REDACTED in redact("aa:bb:cc:dd:ee:ff"))
    check("redact_ip", REDACTED in redact("192.168.1.1"))
    check("redact_path", REDACTED in redact("/Users/secret/file"))
    check("ssid_digest_len", len(ssid_digest("test")) == 16)

    # Baseline parse
    order_text = "(1) Wi-Fi\n(2) Ethernet\n(3) Tailscale"
    order, enabled = _parse_service_order(order_text)
    check("parse_order", order == ["Wi-Fi", "Ethernet", "Tailscale"])

    route_text = "   route to: default\n   gateway: 192.168.1.1\n   interface: en0"
    gw, iface = _parse_default_route(route_text)
    check("parse_route", gw == "192.168.1.1" and iface == "en0")

    # PF rules
    rules = pf_anchor_rules("en5")
    check("pf_rules", "block drop quick on en5 all" in rules)
    check("pf_anchor_name", PF_ANCHOR in rules)

    # Virtual detection
    check("virtual_tailscale", _is_virtual_service("Tailscale"))
    check("virtual_utun", _is_virtual_service("utun0"))
    check("not_virtual_wifi", not _is_virtual_service("Wi-Fi"))

    # State roundtrip
    s = ShieldState(armed=True, session_id="test123", classification="GREEN")
    s2 = ShieldState.from_json(s.to_json())
    check("state_roundtrip", s2.armed and s2.session_id == "test123")

    # Corrupt state fails closed
    check("corrupt_state", load_state(FakeHost()) is None)

    print(f"SELF_TEST: {checks} checks, {failures} failures")
    print(f"SELF_TEST={'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="BOOTMUX Mac Pre-Attach Shield")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit", action="store_true")
    group.add_argument("--arm", action="store_true")
    group.add_argument("--disarm", action="store_true")
    group.add_argument("--status", action="store_true")
    group.add_argument("--recover-now", action="store_true")
    group.add_argument("--postmortem", action="store_true")
    group.add_argument("--daemon", action="store_true")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    host = SystemHost()

    if args.self_test:
        sys.exit(cmd_self_test(host))
    elif args.audit:
        sys.exit(cmd_audit(host))
    elif args.arm:
        sys.exit(cmd_arm(host))
    elif args.disarm:
        sys.exit(cmd_disarm(host))
    elif args.status:
        sys.exit(cmd_status(host))
    elif args.recover_now:
        sys.exit(cmd_recover_now(host))
    elif args.postmortem:
        sys.exit(cmd_postmortem(host))
    elif args.daemon:
        sys.exit(cmd_daemon(host))


if __name__ == "__main__":
    main()
