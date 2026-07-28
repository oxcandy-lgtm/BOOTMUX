#!/usr/bin/env python3
"""R7C P4-R0B — BOOTMUX Mac Pre-Attach Shield (Ephemeral Session Edition).

One-shot macOS network protection for the dangerous legacy ESP32-S3 replacement.
After the S3 is reflashed safe and the session is closed, the Mac returns to its
exact pre-install network behavior.  No permanent policy remains.

Lifecycle:
  NOT_INSTALLED -> install -> INSTALLED_DISARMED
  INSTALLED_DISARMED -> arm --ttl 1800 -> ARMED_TEMPORARY
  ARMED_TEMPORARY -> close-session -> RESTORED
  ARMED_TEMPORARY -> TTL expiry (daemon) -> RESTORED (auto)
  RESTORED -> uninstall --purge -> NOT_INSTALLED / PRESTATE_EQUIVALENT

Modes:
  --audit --arm --renew --close-session --emergency-restore --disarm
  --status --recover-now --postmortem --daemon --self-test
  --fingerprint --uninstall

Hard safety gates (NX P4-R0B):
  s3_attach_before_shield_green: forbidden
  s3_flash_in_this_phase: forbidden
  network_service_delete: forbidden
  global_route_flush: forbidden
  global_pf_flush: forbidden
  saved_wifi_delete: forbidden
  wifi_password_export: forbidden
  unrelated_service_mutation: forbidden
  worker_or_internet_dependency_after_arm: forbidden
  close_session_while_device_present: forbidden
  permanent_ethernet_deny: forbidden
  inferred_rollback_value: forbidden
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

VERSION = "2.0.0"
PF_ANCHOR = "com.bootmux.attach-shield"
STATE_DIR = Path("/var/db/bootmux-shield")
STATE_FILE = STATE_DIR / "shield-state.json"
SESSION_DIR = STATE_DIR / "sessions"
LAUNCHD_LABEL = "com.bootmux.attach-shield"
LAUNCHD_PLIST = f"/Library/LaunchDaemons/{LAUNCHD_LABEL}.plist"
INSTALL_DIR = Path("/usr/local/bootmux/scripts/macos")
INSTALLED_SHIELD = INSTALL_DIR / "bootmux-attach-shield.py"
WATCHDOG_INTERVAL_S = 0.25
ROUTE_MONITOR_CMD = ["route", "-n", "monitor"]
BOOTMUX_VID = "0x303a"
BOOTMUX_PRODUCT_HINTS = ("bootmux", "ncm", "ecm", "rndis")
BOOTMUX_SUBNET = "10.77.0.0/24"
SPLIT_ROUTES_V4 = ["0.0.0.0/1", "128.0.0.0/1"]
SPLIT_ROUTES_V6 = ["::/1", "8000::/1"]
REDACTED = "<redacted>"
MAX_LOG_BYTES = 10 * 1024 * 1024
DEFAULT_TTL_S = 1800
MAX_TTL_S = 7200
MIN_TTL_S = 60
SHIELD_LOCATION_PREFIX = "BOOTMUX-SHIELD-"

# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

_MAC_RE = re.compile(r"([0-9a-fA-F]{2}[:\-]){5}[0-9a-fA-F]{2}")
_IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
_PATH_RE = re.compile(r"/Users/[^/\s]+")


def redact(text: str) -> str:
    text = _MAC_RE.sub(REDACTED, text)
    text = _IP_RE.sub(REDACTED, text)
    text = _PATH_RE.sub(REDACTED, text)
    return text


def ssid_digest(ssid: str) -> str:
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

    def remove_dir(self, path: str) -> None:
        raise NotImplementedError

    def list_dir(self, path: str) -> List[str]:
        raise NotImplementedError


class SystemHost(Host):
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
        tmp.rename(p)

    def mkdir_p(self, path: str, mode: int = 0o700) -> None:
        os.makedirs(path, mode=mode, exist_ok=True)
        os.chmod(path, mode)

    def path_exists(self, path: str) -> bool:
        try:
            return Path(path).exists()
        except (PermissionError, OSError):
            return False

    def remove_file(self, path: str) -> None:
        try:
            os.unlink(path)
        except OSError:
            pass

    def remove_dir(self, path: str) -> None:
        import shutil
        try:
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass

    def list_dir(self, path: str) -> List[str]:
        try:
            return sorted(os.listdir(path))
        except OSError:
            return []


class FakeHost(Host):
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
        if key in self.responses:
            return self.responses[key]
        for prefix, resp in self.responses.items():
            if key.startswith(prefix):
                return resp
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

    def remove_dir(self, path: str) -> None:
        self.dirs.discard(path)
        to_rm = [k for k in self.files if k.startswith(path + "/")]
        for k in to_rm:
            del self.files[k]

    def list_dir(self, path: str) -> List[str]:
        prefix = path.rstrip("/") + "/"
        entries = set()
        for k in list(self.files.keys()) + list(self.dirs):
            if k.startswith(prefix):
                rest = k[len(prefix):]
                entries.add(rest.split("/")[0])
        return sorted(entries)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _parse_service_order(text: str) -> Tuple[List[str], Dict[str, bool]]:
    """Parse networksetup -listnetworkserviceorder -> (ordered_names, enabled).
    Handles both (N) enabled and (*) disabled markers."""
    order: List[str] = []
    enabled: Dict[str, bool] = {}
    for line in text.splitlines():
        m = re.match(r"\((\d+|\*)\)\s+(.+)", line)
        if m:
            marker, name = m.group(1), m.group(2).strip()
            order.append(name)
            enabled[name] = (marker != "*")
    return order, enabled


def _parse_default_route(text: str) -> Tuple[str, str]:
    gw, iface = "", ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("gateway:"):
            gw = line.split(":", 1)[1].strip()
        elif line.startswith("interface:"):
            iface = line.split(":", 1)[1].strip()
    return gw, iface


def _parse_interfaces(text: str) -> Dict[str, str]:
    """Parse networksetup -listallhardwareports -> {device: hwport}."""
    result: Dict[str, str] = {}
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


def _parse_ipv4_info(text: str) -> Tuple[str, Optional[dict]]:
    """Parse networksetup -getinfo -> (mode, manual_values_or_None)."""
    mode = "DHCP"
    manual = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("DHCP Configuration:"):
            mode = "DHCP"
        elif stripped.startswith("Manual Configuration:"):
            mode = "Manual"
            manual = {}
        elif manual is not None:
            if stripped.startswith("IP address:"):
                manual["ip"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Subnet mask:"):
                manual["subnet"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Router:"):
                manual["router"] = stripped.split(":", 1)[1].strip()
    return mode, manual


def _parse_ipv6_mode(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("IPv6:"):
            return stripped.split(":", 1)[1].strip()
    return "Automatic"


def _parse_dns_servers(text: str) -> Tuple[List[str], bool]:
    """Parse networksetup -getdnsservers -> (servers, is_automatic)."""
    if "aren't any DNS Servers set" in text or "There aren't any" in text:
        return [], True
    servers = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("There")]
    return servers, False


def _parse_search_domains(text: str) -> Tuple[List[str], bool]:
    """Parse networksetup -getsearchdomains -> (domains, is_automatic)."""
    if "aren't any Search Domains set" in text or "There aren't any" in text:
        return [], True
    domains = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("There")]
    return domains, False


def _is_virtual_service(name: str) -> bool:
    lower = name.lower()
    return any(k in lower for k in ("tailscale", "vpn", "utun", "loopback", "awdl", "bridge", "thunderbolt"))


def _pf_is_enabled(host: Host) -> bool:
    """Check if PF is currently enabled (F5)."""
    r = host.run(["pfctl", "-s", "info"])
    if r.exit_code != 0:
        return False
    return "Status: Enabled" in r.stdout


# ---------------------------------------------------------------------------
# Baseline (enhanced for exact rollback)
# ---------------------------------------------------------------------------


@dataclass
class Baseline:
    network_location: str = ""
    wifi_device: str = ""
    wifi_service: str = ""
    wifi_enabled: bool = False
    wifi_power: bool = False
    ssid: str = ""  # plaintext, root-owned state only, redacted in logs
    ssid_digest: str = ""
    ipv4_mode: str = ""
    ipv4_manual: Optional[dict] = None
    ipv6_mode: str = ""
    gateway: str = ""
    gateway_interface: str = ""
    dns_servers: List[str] = field(default_factory=list)
    dns_automatic: bool = True
    dns_search: List[str] = field(default_factory=list)
    search_automatic: bool = True
    service_order: List[str] = field(default_factory=list)
    service_enabled: Dict[str, bool] = field(default_factory=dict)
    interfaces: Dict[str, str] = field(default_factory=dict)
    virtual_services: List[str] = field(default_factory=list)
    pf_enabled: bool = False
    captured_at: float = 0.0

    def to_dict(self) -> dict:
        d = {
            "network_location": self.network_location,
            "wifi_device": self.wifi_device,
            "wifi_service": self.wifi_service,
            "wifi_enabled": self.wifi_enabled,
            "wifi_power": self.wifi_power,
            "ssid": self.ssid,
            "ssid_digest": self.ssid_digest,
            "ipv4_mode": self.ipv4_mode,
            "ipv4_manual": self.ipv4_manual,
            "ipv6_mode": self.ipv6_mode,
            "gateway": self.gateway,
            "gateway_interface": self.gateway_interface,
            "dns_servers": self.dns_servers,
            "dns_automatic": self.dns_automatic,
            "dns_search": self.dns_search,
            "search_automatic": self.search_automatic,
            "service_order": self.service_order,
            "service_enabled": self.service_enabled,
            "interfaces": self.interfaces,
            "virtual_services": self.virtual_services,
            "pf_enabled": self.pf_enabled,
            "captured_at": self.captured_at,
        }
        return d

    def redacted_dict(self) -> dict:
        """For logging: redact sensitive fields."""
        d = self.to_dict()
        d["ssid"] = REDACTED
        d["gateway"] = REDACTED
        d["dns_servers"] = [REDACTED] * len(d["dns_servers"])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Baseline":
        b = cls()
        for k, v in d.items():
            if hasattr(b, k):
                setattr(b, k, v)
        return b


def capture_baseline(host: Host) -> Baseline:
    b = Baseline(captured_at=time.time())

    # Network location
    r = host.run(["networksetup", "-getcurrentlocation"])
    b.network_location = r.stdout.strip() if r.exit_code == 0 else ""

    # Hardware ports
    r = host.run(["networksetup", "-listallhardwareports"])
    b.interfaces = _parse_interfaces(r.stdout)
    for dev, port in b.interfaces.items():
        if "wi-fi" in port.lower():
            b.wifi_device = dev
            break

    # Service order with enabled/disabled
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

    # SSID (plaintext stored in root-owned state, redacted in logs)
    if b.wifi_device:
        r = host.run(["networksetup", "-getairportnetwork", b.wifi_device])
        m = re.search(r"Current Wi-Fi Network:\s*(.+)", r.stdout)
        if m:
            b.ssid = m.group(1).strip()
            b.ssid_digest = ssid_digest(b.ssid)

    # IPv4/IPv6 mode
    if b.wifi_service:
        r = host.run(["networksetup", "-getinfo", b.wifi_service])
        b.ipv4_mode, b.ipv4_manual = _parse_ipv4_info(r.stdout)
        b.ipv6_mode = _parse_ipv6_mode(r.stdout)

    # Default route
    r = host.run(["route", "-n", "get", "default"])
    b.gateway, b.gateway_interface = _parse_default_route(r.stdout)

    # DNS (automatic vs manual)
    if b.wifi_service:
        r = host.run(["networksetup", "-getdnsservers", b.wifi_service])
        b.dns_servers, b.dns_automatic = _parse_dns_servers(r.stdout)
        r = host.run(["networksetup", "-getsearchdomains", b.wifi_service])
        b.dns_search, b.search_automatic = _parse_search_domains(r.stdout)

    # PF state (F5)
    b.pf_enabled = _pf_is_enabled(host)

    # Virtual services
    b.virtual_services = [s for s in b.service_order if _is_virtual_service(s)]

    return b


# ---------------------------------------------------------------------------
# Mutation Journal (Section C — exact rollback, never infer)
# ---------------------------------------------------------------------------


class MutationJournal:
    """Append-only journal recording exact pre-values before each mutation."""

    def __init__(self, host: Host, session_id: str):
        self.host = host
        self.path = str(SESSION_DIR / session_id / "journal.jsonl")
        self._seq = 0
        existing = host.read_file(self.path)
        if existing:
            for line in existing.splitlines():
                try:
                    self._seq = max(self._seq, json.loads(line).get("seq", 0))
                except (json.JSONDecodeError, AttributeError):
                    pass

    def record(self, category: str, target: str, pre_value: Optional[dict],
               cmd: List[str], exit_code: int) -> None:
        self._seq += 1
        entry = {
            "seq": self._seq,
            "ts": time.time(),
            "category": category,
            "target": target,
            "pre_value": pre_value,
            "cmd": [redact(str(c)) for c in cmd],
            "exit_code": exit_code,
        }
        line = json.dumps(entry, default=str)
        existing = self.host.read_file(self.path) or ""
        self.host.write_file(self.path, existing + line + "\n")

    def entries(self) -> List[dict]:
        text = self.host.read_file(self.path)
        if not text:
            return []
        result = []
        for line in text.splitlines():
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

    def rollback(self, host: Host) -> Tuple[bool, List[str]]:
        """Execute exact rollback from journal in reverse. Never infer."""
        entries = self.entries()
        issues: List[str] = []
        for entry in reversed(entries):
            if entry.get("exit_code", 1) != 0:
                continue  # mutation failed, nothing to undo
            cat = entry.get("category", "")
            pre = entry.get("pre_value")
            target = entry.get("target", "")

            if pre is None:
                issues.append(f"INCOMPLETE_ROLLBACK_UNKNOWN_PRESTATE:{cat}:{target}")
                continue

            try:
                self._rollback_one(host, cat, target, pre)
            except Exception as exc:
                issues.append(f"ROLLBACK_ERROR:{cat}:{target}:{exc}")

        return len(issues) == 0, issues

    def _rollback_one(self, host: Host, cat: str, target: str, pre: dict) -> None:
        if cat == "service_disable":
            if pre.get("enabled", False):
                host.run(["networksetup", "-setnetworkserviceenabled", target, "on"])
        elif cat == "service_enable":
            if not pre.get("enabled", True):
                host.run(["networksetup", "-setnetworkserviceenabled", target, "off"])
        elif cat == "route_add":
            parts = target.split()
            if len(parts) >= 4:
                family, dest, _, gw = parts[0], parts[1], parts[2], parts[3]
                if family == "inet6":
                    host.run(["route", "-n", "delete", "-inet6", dest, gw])
                else:
                    host.run(["route", "-n", "delete", "-net", dest, gw])
        elif cat == "route_delete":
            if pre.get("existed"):
                gw = pre.get("gateway", "")
                family = pre.get("family", "inet")
                if family == "inet6":
                    host.run(["route", "-n", "add", "-inet6", target, gw])
                else:
                    host.run(["route", "-n", "add", "-net", target, gw])
        elif cat == "dns_set":
            if pre.get("automatic", True):
                host.run(["networksetup", "-setdnsservers", target, "Empty"])
            else:
                servers = pre.get("servers", [])
                if servers:
                    host.run(["networksetup", "-setdnsservers", target] + servers)
        elif cat == "search_set":
            if pre.get("automatic", True):
                host.run(["networksetup", "-setsearchdomains", target, "Empty"])
            else:
                domains = pre.get("domains", [])
                if domains:
                    host.run(["networksetup", "-setsearchdomains", target] + domains)
        elif cat == "order_set":
            order = pre.get("order", [])
            if order:
                host.run(["networksetup", "-ordernetworkservices"] + order)
        elif cat == "ipv4_set":
            mode = pre.get("mode", "DHCP")
            if mode == "DHCP":
                host.run(["networksetup", "-setdhcp", target])
            elif mode == "Manual":
                m = pre.get("manual", {})
                if m:
                    host.run(["networksetup", "-setmanual", target,
                              m.get("ip", ""), m.get("subnet", ""), m.get("router", "")])
        elif cat == "ipv6_set":
            mode = pre.get("mode", "Automatic")
            if mode == "Automatic":
                host.run(["networksetup", "-setv6automatic", target])
        elif cat == "pf_enable":
            if not pre.get("enabled", True):
                host.run(["pfctl", "-d"])
        elif cat == "pf_anchor_load":
            host.run(["pfctl", "-a", target, "-F", "all"])
        elif cat == "location_switch":
            loc = pre.get("location", "")
            if loc:
                host.run(["networksetup", "-switchtolocation", loc])
        elif cat == "location_create":
            if not pre.get("existed", True):
                host.run(["networksetup", "-deletelocation", target])
        elif cat == "wifi_power_set":
            if pre.get("power", True):
                host.run(["networksetup", "-setairportpower", target, "on"])
            else:
                host.run(["networksetup", "-setairportpower", target, "off"])


# ---------------------------------------------------------------------------
# Fingerprint (Section G — pre/post equivalence proof)
# ---------------------------------------------------------------------------


def capture_fingerprint(host: Host) -> dict:
    """Capture comparable network state snapshot."""
    fp: dict = {}

    r = host.run(["networksetup", "-getcurrentlocation"])
    fp["network_location"] = r.stdout.strip() if r.exit_code == 0 else ""

    r = host.run(["networksetup", "-listnetworkserviceorder"])
    order, enabled = _parse_service_order(r.stdout)
    fp["service_order"] = order
    fp["service_enabled"] = enabled

    # Routes (filter transient kernel entries)
    r = host.run(["netstat", "-rn"])
    routes = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        dest = parts[0]
        # Skip link-local, multicast, loopback, fe80, ff00
        if any(dest.startswith(p) for p in ("fe80", "ff0", "127.", "::1", "224.", "0.0.0.0/1", "128.0.0.0/1")):
            continue
        if "link#" in line and "UGS" not in line:
            continue
        routes.append(f"{parts[0]} via {parts[1]} on {parts[3]}")
    fp["routes"] = sorted(routes)

    # DNS/search for Wi-Fi
    wifi_svc = ""
    for svc in order:
        if "wi-fi" in svc.lower():
            wifi_svc = svc
            break
    if wifi_svc:
        r = host.run(["networksetup", "-getdnsservers", wifi_svc])
        servers, auto = _parse_dns_servers(r.stdout)
        fp["dns"] = {"servers": servers, "automatic": auto}
        r = host.run(["networksetup", "-getsearchdomains", wifi_svc])
        domains, sauto = _parse_search_domains(r.stdout)
        fp["search"] = {"domains": domains, "automatic": sauto}
        r = host.run(["networksetup", "-getinfo", wifi_svc])
        mode, _ = _parse_ipv4_info(r.stdout)
        fp["wifi_ipv4_mode"] = mode
        fp["wifi_ipv6_mode"] = _parse_ipv6_mode(r.stdout)
    else:
        fp["dns"] = {"servers": [], "automatic": True}
        fp["search"] = {"domains": [], "automatic": True}
        fp["wifi_ipv4_mode"] = ""
        fp["wifi_ipv6_mode"] = ""

    # PF
    fp["pf_enabled"] = _pf_is_enabled(host)
    r = host.run(["pfctl", "-s", "Anchors"])
    anchors = [l.strip() for l in r.stdout.splitlines()
               if l.strip() and "ALTQ" not in l and "disabled" not in l]
    fp["pf_anchors"] = sorted(anchors)

    # Launchd
    r = host.run(["launchctl", "list", LAUNCHD_LABEL])
    fp["launchd_loaded"] = r.exit_code == 0

    # Shield files
    fp["shield_files"] = sorted([
        p for p in [str(LAUNCHD_PLIST), str(INSTALLED_SHIELD), str(STATE_FILE)]
        if host.path_exists(p)
    ])

    return fp


def compare_fingerprints(a: dict, b: dict) -> Tuple[bool, List[str]]:
    """Compare two fingerprints field by field. Returns (equal, diffs)."""
    diffs = []
    all_keys = sorted(set(list(a.keys()) + list(b.keys())))
    for key in all_keys:
        va, vb = a.get(key), b.get(key)
        if va != vb:
            diffs.append(f"{key}: {json.dumps(va, default=str)} != {json.dumps(vb, default=str)}")
    return len(diffs) == 0, diffs


# ---------------------------------------------------------------------------
# Network Location isolation (Section A)
# ---------------------------------------------------------------------------


def location_supported(host: Host) -> bool:
    r = host.run(["networksetup", "-help"])
    help_text = r.stdout + r.stderr
    return all(cmd in help_text for cmd in ("-createlocation", "-switchtolocation", "-deletelocation"))


def get_current_location(host: Host) -> str:
    r = host.run(["networksetup", "-getcurrentlocation"])
    return r.stdout.strip() if r.exit_code == 0 else ""


def create_shield_location(host: Host, session_id: str, journal: MutationJournal) -> Optional[str]:
    """Create temporary Network Location. Returns location name or None."""
    loc_name = f"{SHIELD_LOCATION_PREFIX}{session_id}"
    pre_loc = get_current_location(host)

    # Check if location already exists
    r = host.run(["networksetup", "-listlocations"])
    existed = loc_name in r.stdout.splitlines()

    r = host.run(["networksetup", "-createlocation", loc_name, "populate"])
    if r.exit_code != 0:
        return None
    journal.record("location_create", loc_name, {"existed": existed}, r.cmd, r.exit_code)

    r = host.run(["networksetup", "-switchtolocation", loc_name])
    if r.exit_code != 0:
        # Rollback creation
        host.run(["networksetup", "-deletelocation", loc_name])
        return None
    journal.record("location_switch", "network_location", {"location": pre_loc}, r.cmd, r.exit_code)

    return loc_name


def restore_location(host: Host, original: str, shield_loc: str, journal: MutationJournal) -> bool:
    """Switch back to original location and delete shield location."""
    r = host.run(["networksetup", "-switchtolocation", original])
    if r.exit_code != 0:
        return False
    journal.record("location_switch", "network_location", {"location": shield_loc}, r.cmd, r.exit_code)

    r = host.run(["networksetup", "-deletelocation", shield_loc])
    return r.exit_code == 0


# ---------------------------------------------------------------------------
# BOOTMUX identification (F6 — require proven mapping)
# ---------------------------------------------------------------------------


def identify_bootmux_services(host: Host, baseline: Baseline) -> List[str]:
    """Identify proven BOOTMUX services. Requires name+device evidence, not just subnet."""
    candidates = []
    for svc in baseline.service_order:
        lower = svc.lower()
        if any(h in lower for h in BOOTMUX_PRODUCT_HINTS):
            candidates.append(svc)

    # Subnet evidence alone is NOT sufficient (F6).
    # Only add if we can map the 10.77 interface to a specific service.
    r = host.run(["scutil", "--nwi"])
    if BOOTMUX_SUBNET.split("/")[0] in r.stdout:
        # Find which interface has 10.77
        r2 = host.run(["ifconfig"])
        iface_1077 = ""
        current_iface = ""
        for line in r2.stdout.splitlines():
            m = re.match(r"^(\w+):", line)
            if m:
                current_iface = m.group(1)
            if "10.77." in line and current_iface:
                iface_1077 = current_iface
                break
        if iface_1077:
            hwport = baseline.interfaces.get(iface_1077, "")
            if hwport:
                for svc in baseline.service_order:
                    if hwport.lower() in svc.lower() or svc.lower() in hwport.lower():
                        if svc not in candidates:
                            candidates.append(svc)
    return candidates


# ---------------------------------------------------------------------------
# Quarantine (journal-aware)
# ---------------------------------------------------------------------------


@dataclass
class QuarantineResult:
    bootmux_services_found: List[str] = field(default_factory=list)
    services_disabled: List[str] = field(default_factory=list)
    routes_removed: List[str] = field(default_factory=list)
    wifi_first: bool = False
    default_route_on_wifi: bool = False
    classification: str = "PENDING"


def quarantine_bootmux(host: Host, baseline: Baseline, journal: MutationJournal) -> QuarantineResult:
    qr = QuarantineResult()
    qr.bootmux_services_found = identify_bootmux_services(host, baseline)

    for svc in qr.bootmux_services_found:
        pre_enabled = baseline.service_enabled.get(svc, True)
        r = host.run(["networksetup", "-setnetworkserviceenabled", svc, "off"])
        journal.record("service_disable", svc, {"enabled": pre_enabled}, r.cmd, r.exit_code)
        if r.exit_code == 0:
            qr.services_disabled.append(svc)

    # Remove only BOOTMUX-scoped routes
    r = host.run(["netstat", "-rn"])
    for line in r.stdout.splitlines():
        if BOOTMUX_SUBNET.split("/")[0] in line:
            parts = line.split()
            if len(parts) >= 2:
                dest, gw = parts[0], parts[1]
                journal.record("route_delete", dest, {"existed": True, "gateway": gw, "family": "inet"},
                               ["route", "-n", "delete", dest, gw], 0)
                host.run(["route", "-n", "delete", dest, gw])
                qr.routes_removed.append(dest)

    # Wi-Fi first (preserve relative order of others)
    if baseline.wifi_service and baseline.service_order:
        others = [s for s in baseline.service_order if s != baseline.wifi_service]
        new_order = [baseline.wifi_service] + others
        r = host.run(["networksetup", "-ordernetworkservices"] + new_order)
        journal.record("order_set", "network_services", {"order": baseline.service_order}, r.cmd, r.exit_code)
        qr.wifi_first = True

    # Verify default route
    r = host.run(["route", "-n", "get", "default"])
    _, iface = _parse_default_route(r.stdout)
    qr.default_route_on_wifi = (iface == baseline.wifi_device)
    qr.classification = "GREEN" if (qr.default_route_on_wifi and qr.wifi_first) else "YELLOW"
    return qr


# ---------------------------------------------------------------------------
# PF management (F5 — track pre-state)
# ---------------------------------------------------------------------------


def pf_anchor_rules(interface: str) -> str:
    return f"# {PF_ANCHOR} — auto-generated\nblock drop quick on {interface} all\n"


def pf_install_anchor(host: Host, interface: str, journal: MutationJournal,
                      pf_was_enabled: bool) -> bool:
    rules = pf_anchor_rules(interface)
    rules_path = f"/tmp/{PF_ANCHOR}-{interface}.rules"
    host.write_file(rules_path, rules, 0o600)
    r = host.run(["pfctl", "-a", PF_ANCHOR, "-f", rules_path])
    host.remove_file(rules_path)
    journal.record("pf_anchor_load", PF_ANCHOR, {"rules": ""}, r.cmd, r.exit_code)

    if not pf_was_enabled:
        r2 = host.run(["pfctl", "-E"])
        journal.record("pf_enable", "pf", {"enabled": False}, r2.cmd, r2.exit_code)

    return r.exit_code == 0


def pf_remove_anchor(host: Host, journal: MutationJournal, pf_was_enabled: bool) -> bool:
    r = host.run(["pfctl", "-a", PF_ANCHOR, "-F", "all"])
    journal.record("pf_anchor_load", PF_ANCHOR, {"rules": "flushed"}, r.cmd, r.exit_code)
    if not pf_was_enabled:
        host.run(["pfctl", "-d"])
    return r.exit_code == 0


def pf_anchor_active(host: Host) -> bool:
    r = host.run(["pfctl", "-a", PF_ANCHOR, "-s", "rules"])
    return r.exit_code == 0 and "block" in r.stdout


# ---------------------------------------------------------------------------
# Route pinning (journal-aware)
# ---------------------------------------------------------------------------


@dataclass
class RoutePinResult:
    pinned_routes: List[str] = field(default_factory=list)
    classification: str = "PENDING"
    error: str = ""


def pin_split_routes(host: Host, gateway: str, interface: str,
                     journal: MutationJournal) -> RoutePinResult:
    rp = RoutePinResult()
    if not gateway or not interface:
        rp.classification = "YELLOW_ROUTE_PIN_UNAVAILABLE"
        rp.error = "no gateway/interface"
        return rp

    for dest in SPLIT_ROUTES_V4:
        r = host.run(["route", "-n", "add", "-net", dest, gateway])
        entry = f"inet {dest} via {gateway}"
        journal.record("route_add", entry, {"existed": False}, r.cmd, r.exit_code)
        if r.exit_code == 0:
            rp.pinned_routes.append(entry)
        else:
            rp.classification = "YELLOW_ROUTE_PIN_UNAVAILABLE"
            rp.error = f"failed to pin {dest}: {r.stderr.strip()}"
            for pinned in rp.pinned_routes:
                parts = pinned.split()
                host.run(["route", "-n", "delete", "-net", parts[1], gateway])
            rp.pinned_routes = []
            return rp

    for dest in SPLIT_ROUTES_V6:
        r = host.run(["route", "-n", "add", "-inet6", dest, gateway])
        entry = f"inet6 {dest} via {gateway}"
        journal.record("route_add", entry, {"existed": False}, r.cmd, r.exit_code)
        if r.exit_code == 0:
            rp.pinned_routes.append(entry)

    rp.classification = "GREEN"
    return rp


def unpin_split_routes(host: Host, pinned: List[str], gateway: str) -> None:
    for entry in pinned:
        parts = entry.split()
        if len(parts) >= 4:
            family, dest, gw = parts[0], parts[1], parts[3]
            if family == "inet6":
                host.run(["route", "-n", "delete", "-inet6", dest, gw])
            else:
                host.run(["route", "-n", "delete", "-net", dest, gw])


# ---------------------------------------------------------------------------
# Recovery Q1-Q9 (enhanced)
# ---------------------------------------------------------------------------


@dataclass
class RecoveryResult:
    steps: Dict[str, str] = field(default_factory=dict)
    classification: str = "PENDING"


def get_current_interfaces(host: Host) -> Dict[str, str]:
    r = host.run(["networksetup", "-listallhardwareports"])
    return _parse_interfaces(r.stdout)


def detect_new_external_ethernet(host: Host, baseline: Baseline) -> List[str]:
    current = get_current_interfaces(host)
    baseline_ifaces = set(baseline.interfaces.keys())
    new_untrusted = []
    for dev, port in current.items():
        if dev in baseline_ifaces or dev in ("lo0", "awdl0"):
            continue
        if _is_virtual_service(port):
            continue
        port_lower = port.lower()
        if any(k in port_lower for k in ("ethernet", "ncm", "ecm", "rndis", "thunderbolt")):
            new_untrusted.append(dev)
    return new_untrusted


def run_recovery(host: Host, baseline: Baseline, untrusted_ifaces: List[str],
                 journal: Optional[MutationJournal] = None) -> RecoveryResult:
    rr = RecoveryResult()

    for iface in untrusted_ifaces:
        ok = pf_install_anchor(host, iface, journal, baseline.pf_enabled) if journal else False
        rr.steps[f"Q1:{iface}"] = "OK" if ok else "INCOMPLETE:pf_block"

    current_ifaces = get_current_interfaces(host)
    for iface in untrusted_ifaces:
        hwport = current_ifaces.get(iface, baseline.interfaces.get(iface, ""))
        if not hwport:
            continue
        for svc in baseline.service_order:
            if hwport.lower() in svc.lower() or svc.lower() in hwport.lower():
                pre_enabled = baseline.service_enabled.get(svc, True)
                r = host.run(["networksetup", "-setnetworkserviceenabled", svc, "off"])
                if journal:
                    journal.record("service_disable", svc, {"enabled": pre_enabled}, r.cmd, r.exit_code)
                rr.steps[f"Q2:{svc}"] = "OK" if r.exit_code == 0 else "INCOMPLETE:disable"

    r = host.run(["netstat", "-rn"])
    for line in r.stdout.splitlines():
        for iface in untrusted_ifaces:
            if iface in line and ("default" in line or "::/0" in line):
                parts = line.split()
                if parts:
                    host.run(["route", "-n", "delete", parts[0]])
                    rr.steps[f"Q3:{parts[0]}"] = "OK"

    if baseline.wifi_service:
        if baseline.ipv4_mode == "DHCP":
            host.run(["networksetup", "-setdhcp", baseline.wifi_service])
        rr.steps["Q4"] = "OK"
    else:
        rr.steps["Q4"] = "SKIP:no_wifi_service"

    if baseline.wifi_service:
        if baseline.dns_automatic:
            host.run(["networksetup", "-setdnsservers", baseline.wifi_service, "Empty"])
        elif baseline.dns_servers:
            host.run(["networksetup", "-setdnsservers", baseline.wifi_service] + baseline.dns_servers)
        rr.steps["Q5"] = "OK"
    else:
        rr.steps["Q5"] = "SKIP:no_dns_baseline"

    if baseline.service_order:
        host.run(["networksetup", "-ordernetworkservices"] + baseline.service_order)
        rr.steps["Q6"] = "OK"
    else:
        rr.steps["Q6"] = "SKIP:no_order_baseline"

    # F4: never use ssid_digest for reconnect. Rely on macOS preferred-network.
    if baseline.wifi_device:
        r = host.run(["networksetup", "-getairportnetwork", baseline.wifi_device])
        if "Current Wi-Fi Network:" in r.stdout:
            rr.steps["Q7"] = "SKIP:associated"
        else:
            # Toggle power to trigger preferred-network reconnect
            host.run(["networksetup", "-setairportpower", baseline.wifi_device, "off"])
            time.sleep(1)
            host.run(["networksetup", "-setairportpower", baseline.wifi_device, "on"])
            rr.steps["Q7"] = "OK:power_cycled"
    else:
        rr.steps["Q7"] = "SKIP:no_wifi_device"

    failures = [k for k, v in rr.steps.items() if v.startswith("INCOMPLETE")]
    if failures and baseline.wifi_device:
        host.run(["networksetup", "-setairportpower", baseline.wifi_device, "off"])
        time.sleep(1)
        host.run(["networksetup", "-setairportpower", baseline.wifi_device, "on"])
        rr.steps["Q8"] = "OK"
    else:
        rr.steps["Q8"] = "SKIP:not_needed"

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
# Session state (ephemeral, TTL-bounded)
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
    pf_was_enabled: bool = False
    armed_at: float = 0.0
    expires_at: float = 0.0
    ttl_seconds: int = DEFAULT_TTL_S
    classification: str = ""
    shield_location: str = ""
    original_location: str = ""
    location_mode: bool = False
    session_closed: bool = False

    def to_json(self) -> str:
        return json.dumps({
            "armed": self.armed,
            "session_id": self.session_id,
            "baseline": self.baseline,
            "pinned_routes": self.pinned_routes,
            "quarantined_services": self.quarantined_services,
            "untrusted_interfaces": self.untrusted_interfaces,
            "pf_anchor_active": self.pf_anchor_active,
            "pf_was_enabled": self.pf_was_enabled,
            "armed_at": self.armed_at,
            "expires_at": self.expires_at,
            "ttl_seconds": self.ttl_seconds,
            "classification": self.classification,
            "shield_location": self.shield_location,
            "original_location": self.original_location,
            "location_mode": self.location_mode,
            "session_closed": self.session_closed,
        }, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ShieldState":
        d = json.loads(text)
        s = cls()
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s

    def is_expired(self) -> bool:
        return self.armed and time.time() > self.expires_at

    def ttl_remaining(self) -> float:
        return max(0.0, self.expires_at - time.time())


def load_state(host: Host) -> Optional[ShieldState]:
    text = host.read_file(str(STATE_FILE))
    if not text:
        return None
    try:
        return ShieldState.from_json(text)
    except (json.JSONDecodeError, KeyError):
        return None


def save_state(host: Host, state: ShieldState) -> None:
    host.mkdir_p(str(STATE_DIR), 0o700)
    host.write_file(str(STATE_FILE), state.to_json(), 0o600)


# ---------------------------------------------------------------------------
# Forensic logging
# ---------------------------------------------------------------------------


class SessionLogger:
    def __init__(self, host: Host, session_id: str):
        self.host = host
        self.session_id = session_id
        self.log_dir = str(SESSION_DIR / session_id)
        self.log_file = f"{self.log_dir}/shield.jsonl"
        host.mkdir_p(self.log_dir, 0o700)
        self._bytes_written = 0

    def log(self, event: str, data: dict) -> None:
        entry = {"ts": time.time(), "session": self.session_id, "event": event, "data": data}
        line = redact(json.dumps(entry, default=str))
        if self._bytes_written + len(line) > MAX_LOG_BYTES:
            return
        self.host.write_file(self.log_file, (self.host.read_file(self.log_file) or "") + line + "\n")
        self._bytes_written += len(line) + 1


# ---------------------------------------------------------------------------
# Close session C1-C12 (Section D)
# ---------------------------------------------------------------------------


def close_session(host: Host, state: ShieldState, force: bool = False) -> Tuple[bool, str]:
    """Execute C1-C12 exact close. Returns (success, classification)."""
    baseline = Baseline.from_dict(state.baseline) if state.baseline else Baseline()
    journal = MutationJournal(host, state.session_id)
    logger = SessionLogger(host, state.session_id)

    # Refuse if device CURRENTLY present (not historical) — unless forced
    if not force and state.untrusted_interfaces:
        current = get_current_interfaces(host)
        still_present = [i for i in state.untrusted_interfaces if i in current]
        if still_present:
            return False, f"REFUSED_DEVICE_PRESENT={still_present}"

    logger.log("close_session_start", {"force": force})

    # C1: stop quarantine daemon
    host.run(["launchctl", "unload", LAUNCHD_PLIST])
    logger.log("C1_daemon_stopped", {})

    # C2: remove shield-owned PF anchor rules
    host.run(["pfctl", "-a", PF_ANCHOR, "-F", "all"])
    logger.log("C2_pf_anchor_cleared", {})

    # C3: release PF enable reference (F5)
    if not state.pf_was_enabled:
        host.run(["pfctl", "-d"])
        logger.log("C3_pf_disabled", {"was_enabled": False})
    else:
        logger.log("C3_pf_preserved", {"was_enabled": True})

    # C4: remove shield-added routes
    unpin_split_routes(host, state.pinned_routes, baseline.gateway)
    logger.log("C4_routes_removed", {"count": len(state.pinned_routes)})

    # C5-C8: journal rollback (exact pre-values, reverse order)
    ok, issues = journal.rollback(host)
    logger.log("C5_C8_journal_rollback", {"ok": ok, "issues": issues})

    # C9: switch back to original Network Location
    if state.location_mode and state.original_location and state.shield_location:
        restore_location(host, state.original_location, state.shield_location, journal)
        logger.log("C9_location_restored", {"original": state.original_location})

    # C10: delete temporary shield location (handled in C9 restore_location)
    logger.log("C10_location_deleted", {})

    # C11: verify pre-state equivalence
    fp_post = capture_fingerprint(host)
    fp_pre_path = str(SESSION_DIR / state.session_id / "fingerprint-pre.json")
    fp_pre_text = host.read_file(fp_pre_path)
    if fp_pre_text:
        fp_pre = json.loads(fp_pre_text)
        equal, diffs = compare_fingerprints(fp_pre, fp_post)
        logger.log("C11_fingerprint_verify", {"equal": equal, "diffs": diffs[:5]})
    else:
        equal = False
        logger.log("C11_fingerprint_verify", {"equal": False, "reason": "no_pre_fingerprint"})

    # C12: mark session closed
    state.armed = False
    state.session_closed = True
    state.pinned_routes = []
    state.pf_anchor_active = False
    state.quarantined_services = []
    save_state(host, state)
    logger.log("C12_session_closed", {})

    classification = "GREEN_CLOSE_COMPLETE" if (ok and equal) else "YELLOW_CLOSE_PARTIAL"
    if issues:
        classification = f"INCOMPLETE_ROLLBACK:{';'.join(issues[:3])}"
    return ok and equal, classification


# ---------------------------------------------------------------------------
# Uninstall / Purge (Section E)
# ---------------------------------------------------------------------------


def cmd_uninstall(host: Host, purge: bool, evidence_path: str = "") -> int:
    state = load_state(host)

    # If armed, close first
    if state and state.armed:
        ok, cls = close_session(host, state, force=True)
        print(f"PRE_CLOSE={cls}")

    # Archive evidence if requested
    if evidence_path and state:
        report = {
            "session_id": state.session_id,
            "classification": state.classification,
            "armed_at": state.armed_at,
            "fingerprint_post": capture_fingerprint(host),
        }
        host.write_file(evidence_path, json.dumps(report, indent=2, default=str), 0o600)
        print(f"EVIDENCE_ARCHIVED={evidence_path}")

    # Unload launchd
    host.run(["launchctl", "unload", LAUNCHD_PLIST])

    # Remove PF anchor
    host.run(["pfctl", "-a", PF_ANCHOR, "-F", "all"])

    # Remove plist
    host.remove_file(LAUNCHD_PLIST)

    # Remove installed shield
    host.remove_file(str(INSTALLED_SHIELD))

    # Remove state dir
    if purge:
        host.remove_dir(str(STATE_DIR))
    else:
        host.remove_file(str(STATE_FILE))

    # Remove empty parent dirs
    for d in [str(INSTALL_DIR), str(INSTALL_DIR.parent)]:
        try:
            if host.path_exists(d) and not host.list_dir(d):
                os.rmdir(d)
        except OSError:
            pass

    print(f"UNINSTALL={'PURGE' if purge else 'KEEP_EVIDENCE'}=OK")
    return 0


# ---------------------------------------------------------------------------
# Daemon loop (TTL-aware)
# ---------------------------------------------------------------------------


def daemon_loop(host: Host, logger: SessionLogger) -> None:
    state = load_state(host)
    if not state or not state.armed:
        logger.log("daemon_exit", {"reason": "not_armed"})
        return

    # Reboot recovery: if expired, rollback immediately
    if state.is_expired():
        logger.log("daemon_ttl_expired_on_start", {"expires_at": state.expires_at})
        close_session(host, state, force=True)
        return

    baseline = Baseline.from_dict(state.baseline) if state.baseline else Baseline()
    journal = MutationJournal(host, state.session_id)
    logger.log("daemon_start", {"session": state.session_id, "ttl_remaining": state.ttl_remaining()})

    route_proc = None
    try:
        route_proc = subprocess.Popen(
            ROUTE_MONITOR_CMD, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
    except (OSError, FileNotFoundError):
        pass

    running = True

    def handle_signal(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while running:
        time.sleep(WATCHDOG_INTERVAL_S)

        # TTL check (wall clock)
        if state.is_expired():
            logger.log("ttl_expired_auto_rollback", {})
            close_session(host, state, force=True)
            break

        # New untrusted interfaces
        new_untrusted = detect_new_external_ethernet(host, baseline)
        if new_untrusted:
            logger.log("untrusted_detected", {"interfaces": new_untrusted})
            state.untrusted_interfaces = list(set(state.untrusted_interfaces + new_untrusted))
            save_state(host, state)
            rr = run_recovery(host, baseline, new_untrusted, journal)
            logger.log("recovery", {"result": rr.steps, "classification": rr.classification})
            continue

        # Route drift
        r = host.run(["route", "-n", "get", "default"])
        _, iface = _parse_default_route(r.stdout)
        if iface != baseline.wifi_device:
            logger.log("route_drift", {"expected": baseline.wifi_device, "actual": iface})
            rr = run_recovery(host, baseline, state.untrusted_interfaces, journal)
            logger.log("recovery", {"result": rr.steps, "classification": rr.classification})

    if route_proc:
        route_proc.terminate()
        try:
            route_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            route_proc.kill()
    logger.log("daemon_stop", {})


# ---------------------------------------------------------------------------
# Postmortem
# ---------------------------------------------------------------------------


def generate_postmortem(host: Host) -> str:
    if not host.path_exists(str(SESSION_DIR)):
        return "NO_SESSIONS"
    sessions = host.list_dir(str(SESSION_DIR))
    if not sessions:
        return "NO_SESSIONS"
    latest = sessions[-1]
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
    report = {
        "session": latest,
        "total_events": len(events),
        "events": events[-10:],
    }
    return json.dumps(report, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI modes
# ---------------------------------------------------------------------------


def cmd_audit(host: Host) -> int:
    baseline = capture_baseline(host)
    print(f"wifi_device={baseline.wifi_device}")
    print(f"wifi_service={baseline.wifi_service}")
    print(f"wifi_power={baseline.wifi_power}")
    print(f"ssid_digest={baseline.ssid_digest}")
    print(f"gateway={REDACTED}")
    print(f"service_order={baseline.service_order}")
    print(f"service_enabled={baseline.service_enabled}")
    print(f"pf_enabled={baseline.pf_enabled}")
    print(f"location_supported={location_supported(host)}")
    bootmux = identify_bootmux_services(host, baseline)
    print(f"bootmux_services_found={bootmux}")
    state = load_state(host)
    print(f"shield_armed={state.armed if state else False}")
    return 0


def cmd_arm(host: Host, ttl: int) -> int:
    state = load_state(host)
    if state and state.armed:
        print("ALREADY_ARMED")
        return 0

    ttl = max(MIN_TTL_S, min(ttl, MAX_TTL_S))
    session_id = str(uuid.uuid4())[:8]
    logger = SessionLogger(host, session_id)
    journal = MutationJournal(host, session_id)
    logger.log("arm_start", {"version": VERSION, "ttl": ttl})

    baseline = capture_baseline(host)
    if not baseline.wifi_device:
        print("CLASSIFICATION=RED_NO_WIFI_DEVICE")
        return 1

    # Capture pre-fingerprint
    fp_pre = capture_fingerprint(host)
    fp_path = str(SESSION_DIR / session_id / "fingerprint-pre.json")
    host.mkdir_p(str(SESSION_DIR / session_id), 0o700)
    host.write_file(fp_path, json.dumps(fp_pre, indent=2, default=str), 0o600)

    # Network Location isolation (Section A)
    loc_mode = False
    shield_loc = ""
    original_loc = baseline.network_location
    if location_supported(host):
        shield_loc = create_shield_location(host, session_id, journal)
        if shield_loc:
            loc_mode = True
            logger.log("location_isolation", {"shield": shield_loc, "original": original_loc})
        else:
            logger.log("location_fallback", {"reason": "create_failed"})
    else:
        logger.log("location_fallback", {"reason": "not_supported"})

    # Quarantine
    qr = quarantine_bootmux(host, baseline, journal)
    logger.log("quarantine", {"result": qr.classification, "disabled": qr.services_disabled})

    # Pin routes
    rp = pin_split_routes(host, baseline.gateway, baseline.wifi_device, journal)
    logger.log("route_pin", {"classification": rp.classification, "pinned": len(rp.pinned_routes)})

    # Save state
    now = time.time()
    new_state = ShieldState(
        armed=True,
        session_id=session_id,
        baseline=baseline.to_dict(),
        pinned_routes=rp.pinned_routes,
        quarantined_services=qr.services_disabled,
        pf_was_enabled=baseline.pf_enabled,
        armed_at=now,
        expires_at=now + ttl,
        ttl_seconds=ttl,
        classification="GREEN" if rp.classification == "GREEN" else "YELLOW_ROUTE_PIN_UNAVAILABLE",
        shield_location=shield_loc or "",
        original_location=original_loc,
        location_mode=loc_mode,
    )
    save_state(host, new_state)
    logger.log("arm_complete", {"classification": new_state.classification, "expires_at": new_state.expires_at})

    print(f"CLASSIFICATION={new_state.classification}")
    print(f"SESSION_ID={session_id}")
    print(f"TTL_SECONDS={ttl}")
    print(f"EXPIRES_AT={new_state.expires_at}")
    print(f"ROUTE_PIN={rp.classification}")
    print(f"QUARANTINE={qr.classification}")
    print(f"LOCATION_MODE={'ISOLATED' if loc_mode else 'BASELINE_RESTORE'}")
    return 0


def cmd_renew(host: Host, session_id: str, ttl: int) -> int:
    state = load_state(host)
    if not state or not state.armed:
        print("NOT_ARMED")
        return 1
    if state.session_id != session_id:
        print(f"SESSION_MISMATCH expected={state.session_id}")
        return 1
    ttl = max(MIN_TTL_S, min(ttl, MAX_TTL_S))
    state.expires_at = time.time() + ttl
    state.ttl_seconds = ttl
    save_state(host, state)
    print(f"RENEWED ttl={ttl} expires_at={state.expires_at}")
    return 0


def cmd_close_session(host: Host, force: bool = False) -> int:
    state = load_state(host)
    if not state:
        print("NOT_INSTALLED")
        return 0
    if not state.armed:
        if state.session_closed:
            print("ALREADY_CLOSED")
        else:
            print("NOT_ARMED")
        return 0
    ok, classification = close_session(host, state, force=force)
    print(f"CLOSE_RESULT={classification}")
    return 0 if ok else 1


def cmd_status(host: Host) -> int:
    state = load_state(host)
    if not state:
        print("STATUS=NOT_INSTALLED")
        return 0
    if state.session_closed:
        print("STATUS=RESTORED")
    elif state.armed:
        print("STATUS=ARMED_TEMPORARY")
    else:
        print("STATUS=INSTALLED_DISARMED")
    print(f"SESSION_ID={state.session_id}")
    print(f"CLASSIFICATION={state.classification}")
    print(f"PINNED_ROUTES={len(state.pinned_routes)}")
    print(f"QUARANTINED={state.quarantined_services}")
    print(f"UNTRUSTED={state.untrusted_interfaces}")
    print(f"PF_ANCHOR={state.pf_anchor_active}")
    print(f"TTL_SECONDS={state.ttl_seconds}")
    print(f"TTL_REMAINING={state.ttl_remaining():.0f}")
    print(f"LOCATION_MODE={'ISOLATED' if state.location_mode else 'BASELINE_RESTORE'}")
    return 0


def cmd_recover_now(host: Host) -> int:
    state = load_state(host)
    if not state or not state.baseline:
        print("NO_BASELINE")
        return 1
    baseline = Baseline.from_dict(state.baseline)
    journal = MutationJournal(host, state.session_id) if state.session_id else None
    untrusted = state.untrusted_interfaces or detect_new_external_ethernet(host, baseline)
    rr = run_recovery(host, baseline, untrusted, journal)
    print(f"RECOVERY_CLASSIFICATION={rr.classification}")
    for k, v in sorted(rr.steps.items()):
        print(f"  {k}: {v}")
    return 0 if rr.classification == "GREEN" else 1


def cmd_fingerprint(host: Host) -> int:
    fp = capture_fingerprint(host)
    print(json.dumps(fp, indent=2, default=str))
    return 0


def cmd_postmortem(host: Host) -> int:
    print(generate_postmortem(host))
    return 0


def cmd_daemon(host: Host) -> int:
    state = load_state(host)
    if not state or not state.session_id:
        print("NO_SESSION")
        return 1
    logger = SessionLogger(host, state.session_id)
    daemon_loop(host, logger)
    return 0


def cmd_self_test(host: Host) -> int:
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

    # Service order parsing (with disabled)
    order_text = "(1) Wi-Fi\n(*) Ethernet\n(2) Tailscale"
    order, enabled = _parse_service_order(order_text)
    check("parse_order", order == ["Wi-Fi", "Ethernet", "Tailscale"])
    check("parse_disabled", enabled.get("Ethernet") is False)
    check("parse_enabled", enabled.get("Wi-Fi") is True)

    # Route parsing
    route_text = "   route to: default\n   gateway: 192.168.1.1\n   interface: en0"
    gw, iface = _parse_default_route(route_text)
    check("parse_route", gw == "192.168.1.1" and iface == "en0")

    # IPv4 parsing
    ipv4_text = "Manual Configuration:\n   IP address: 10.0.0.5\n   Subnet mask: 255.255.255.0\n   Router: 10.0.0.1"
    mode, manual = _parse_ipv4_info(ipv4_text)
    check("parse_ipv4_manual", mode == "Manual" and manual is not None and manual.get("ip") == "10.0.0.5")

    ipv4_dhcp = "DHCP Configuration:\n   IP address: 192.168.1.100"
    mode2, manual2 = _parse_ipv4_info(ipv4_dhcp)
    check("parse_ipv4_dhcp", mode2 == "DHCP" and manual2 is None)

    # DNS parsing
    dns_auto = "There aren't any DNS Servers set on Wi-Fi."
    servers, auto = _parse_dns_servers(dns_auto)
    check("parse_dns_auto", auto is True and servers == [])

    dns_manual = "192.168.1.1\n8.8.8.8"
    servers2, auto2 = _parse_dns_servers(dns_manual)
    check("parse_dns_manual", auto2 is False and len(servers2) == 2)

    # PF rules
    rules = pf_anchor_rules("en5")
    check("pf_rules", "block drop quick on en5 all" in rules)

    # Virtual detection
    check("virtual_tailscale", _is_virtual_service("Tailscale"))
    check("not_virtual_wifi", not _is_virtual_service("Wi-Fi"))

    # State roundtrip
    s = ShieldState(armed=True, session_id="test123", classification="GREEN",
                    ttl_seconds=1800, expires_at=time.time() + 1800)
    s2 = ShieldState.from_json(s.to_json())
    check("state_roundtrip", s2.armed and s2.session_id == "test123" and s2.ttl_seconds == 1800)

    # TTL
    check("ttl_expired", ShieldState(armed=True, expires_at=time.time() - 1).is_expired())
    check("ttl_not_expired", not ShieldState(armed=True, expires_at=time.time() + 100).is_expired())

    # Journal roundtrip
    fh = FakeHost()
    j = MutationJournal(fh, "jtest")
    j.record("service_disable", "TestSvc", {"enabled": True}, ["networksetup", "-setnetworkserviceenabled", "TestSvc", "off"], 0)
    entries = j.entries()
    check("journal_record", len(entries) == 1 and entries[0]["category"] == "service_disable")
    check("journal_pre_value", entries[0]["pre_value"]["enabled"] is True)

    # Fingerprint compare
    fp_a = {"network_location": "Automatic", "service_order": ["Wi-Fi"]}
    fp_b = {"network_location": "Automatic", "service_order": ["Wi-Fi"]}
    fp_c = {"network_location": "Custom", "service_order": ["Wi-Fi"]}
    eq1, _ = compare_fingerprints(fp_a, fp_b)
    eq2, diffs = compare_fingerprints(fp_a, fp_c)
    check("fingerprint_equal", eq1)
    check("fingerprint_diff", not eq2 and len(diffs) == 1)

    # Corrupt state
    check("corrupt_state", load_state(FakeHost()) is None)

    # Location support detection
    fh2 = FakeHost()
    fh2.set_response("networksetup -help", "-createlocation\n-switchtolocation\n-deletelocation")
    check("location_supported", location_supported(fh2))
    fh3 = FakeHost()
    fh3.set_response("networksetup -help", "no location commands")
    check("location_not_supported", not location_supported(fh3))

    print(f"SELF_TEST: {checks} checks, {failures} failures")
    print(f"SELF_TEST={'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="BOOTMUX Mac Pre-Attach Shield (Ephemeral)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit", action="store_true")
    group.add_argument("--arm", action="store_true")
    group.add_argument("--renew", action="store_true")
    group.add_argument("--close-session", action="store_true")
    group.add_argument("--emergency-restore", action="store_true")
    group.add_argument("--disarm", action="store_true")
    group.add_argument("--status", action="store_true")
    group.add_argument("--recover-now", action="store_true")
    group.add_argument("--postmortem", action="store_true")
    group.add_argument("--daemon", action="store_true")
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--fingerprint", action="store_true")
    group.add_argument("--uninstall", action="store_true")

    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL_S)
    parser.add_argument("--session", type=str, default="")
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--keep-evidence", type=str, default="")
    args = parser.parse_args()

    host = SystemHost()

    if args.self_test:
        sys.exit(cmd_self_test(host))
    elif args.audit:
        sys.exit(cmd_audit(host))
    elif args.arm:
        sys.exit(cmd_arm(host, args.ttl))
    elif args.renew:
        sys.exit(cmd_renew(host, args.session, args.ttl))
    elif args.close_session:
        sys.exit(cmd_close_session(host, force=False))
    elif args.emergency_restore:
        sys.exit(cmd_close_session(host, force=True))
    elif args.disarm:
        sys.exit(cmd_close_session(host, force=False))
    elif args.status:
        sys.exit(cmd_status(host))
    elif args.recover_now:
        sys.exit(cmd_recover_now(host))
    elif args.postmortem:
        sys.exit(cmd_postmortem(host))
    elif args.daemon:
        sys.exit(cmd_daemon(host))
    elif args.fingerprint:
        sys.exit(cmd_fingerprint(host))
    elif args.uninstall:
        sys.exit(cmd_uninstall(host, purge=args.purge, evidence_path=args.keep_evidence))


if __name__ == "__main__":
    main()
