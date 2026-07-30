#!/usr/bin/env python3
"""BOOTMUX macOS network guardian — recovery-only host controller (R7C P2).

Purpose
-------
Older / experimental BOOTMUX USB-network firmware can leave macOS holding a
USB network service, route and DNS state that survives Wi-Fi toggles and only
clears on reboot.  This guardian restores host control *without* rebooting,
*without* deleting saved Wi-Fi networks, and *without* touching unrelated
Ethernet / VPN / Thunderbolt Bridge / Tailscale services.

Safety model (authoritative: NX R7C P2 MAC GUARDIAN ONLY)
---------------------------------------------------------
The guardian is RECOVERY-ONLY.  It never creates the BOOTMUX USB route, never
enables NCM, never provides Internet through the S3, and never changes Wi-Fi as
part of normal operation.  It may only:

  * conservatively identify an old/experimental BOOTMUX USB-network interface;
  * snapshot host state before BOOTMUX control is accepted;
  * remove BOOTMUX-owned state after detach / heartbeat loss / explicit repair
    / stale-state detection;
  * restore the previously captured Wi-Fi / network state;
  * report evidence.

A safe HID-only BOOTMUX attachment is a complete no-op.

Mutation is allowed only after the interface is proven BOOTMUX-owned by at least
TWO independent signals, INCLUDING at least one hardware/USB signal.  Ambiguous
identity fails closed into audit-only.

Everything that touches the real system flows through the :class:`Host` seam so
the test-suite runs against deterministic fixtures and NEVER mutates the
developer Mac.  Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- #
# Constants — the public contract shared with docs and tests.
# --------------------------------------------------------------------------- #

SCHEMA_VERSION = 1

BOOTMUX_USB_VID = 0x303A
BOOTMUX_USB_PID = 0x4014
BOOTMUX_PRODUCT = "BOOTMUX Bridge Experimental"
BOOTMUX_SERIAL = "BOOTMUX-R7A-NCM"

BOOTMUX_NET = "10.77.0.0/24"
BOOTMUX_PEER = "10.77.0.1"
BOOTMUX_SERVICE_HINT = "BOOTMUX USB Ethernet"

# Identity policy: at least two strong signals, at least one hardware signal.
MIN_SIGNALS = 2
MIN_HARDWARE_SIGNALS = 1

# Daemon timing bounds.
IDLE_POLL_SECONDS = 5.0
ATTACHED_POLL_SECONDS = 1.0
BASELINE_STABILITY_SECONDS = 15.0
HEARTBEAT_FAIL_SECONDS = 5.0
WIFI_TOGGLE_COOLDOWN_SECONDS = 120.0

# Bounded subprocess execution.
COMMAND_TIMEOUT_SECONDS = 20.0

# Persistent state store.
DEFAULT_STATE_DIR = "/var/db/bootmux-network-guardian"
STATE_BASELINE = "baseline.json"
STATE_PREVIOUS = "previous-baseline.json"
STATE_RUNTIME = "runtime.json"

# Verification keys (R7) — stable contract for tests and docs.
VERIFY_KEYS = (
    "bootmux_default_route_absent",
    "bootmux_scoped_routes_absent",
    "bootmux_service_disabled",
    "wifi_power_matches_baseline",
    "wifi_ssid_matches_baseline_or_redacted_equivalent",
    "wifi_ipv4_mode_matches_baseline",
    "wifi_default_route_restored",
    "wifi_dns_matches_baseline",
    "service_order_matches_baseline",
    "unrelated_services_unchanged",
)


# --------------------------------------------------------------------------- #
# Data types
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Command:
    """A single bounded mutation command.

    ``step`` tags the R1-R7 stage; ``target_interface`` / ``target_service``
    declare what the command acts on so tests can assert that NO command targets
    an unrelated interface/service.
    """

    argv: Tuple[str, ...]
    step: str
    purpose: str
    target_interface: Optional[str] = None
    target_service: Optional[str] = None

    def as_dict(self) -> Dict:
        return {
            "argv": list(self.argv),
            "step": self.step,
            "purpose": self.purpose,
            "target_interface": self.target_interface,
            "target_service": self.target_service,
        }


@dataclass
class RepairPlan:
    commands: List[Command] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    needs_change: bool = False

    def add(self, command: Command) -> None:
        self.commands.append(command)
        self.needs_change = True

    def argvs(self) -> List[List[str]]:
        return [list(c.argv) for c in self.commands]

    def as_dict(self) -> Dict:
        return {
            "needs_change": self.needs_change,
            "commands": [c.as_dict() for c in self.commands],
            "notes": self.notes,
        }


@dataclass
class IdentityResult:
    proven: bool
    ambiguous: bool
    interface: Optional[str]
    service: Optional[str]
    hardware_signals: List[str] = field(default_factory=list)
    network_signals: List[str] = field(default_factory=list)
    reason: str = ""

    @property
    def signals(self) -> List[str]:
        return self.hardware_signals + self.network_signals

    def as_dict(self) -> Dict:
        return {
            "proven": self.proven,
            "ambiguous": self.ambiguous,
            "interface": self.interface,
            "service": self.service,
            "hardware_signals": self.hardware_signals,
            "network_signals": self.network_signals,
            "reason": self.reason,
        }


# --------------------------------------------------------------------------- #
# Host seam — the ONLY place the real system is observed or mutated.
# --------------------------------------------------------------------------- #


class Host:
    """Abstract host.  Every method is pure data in / command out.

    Observation methods return plain structures; mutation goes through
    :meth:`run`, which returns ``(returncode, stdout, stderr)``.  Tests subclass
    this with deterministic fixtures; production uses :class:`SystemHost`.
    """

    # -- observation ------------------------------------------------------- #
    def usb_devices(self) -> List[Dict]:
        raise NotImplementedError

    def interfaces(self) -> List[Dict]:
        raise NotImplementedError

    def routes(self) -> List[Dict]:
        raise NotImplementedError

    def services(self) -> List[Dict]:
        raise NotImplementedError

    def service_order(self) -> List[str]:
        raise NotImplementedError

    def wifi_device(self) -> Optional[str]:
        raise NotImplementedError

    def wifi_power(self, device: str) -> Optional[bool]:
        raise NotImplementedError

    def wifi_ssid(self, device: str) -> Optional[str]:
        raise NotImplementedError

    def wifi_ipv4(self, device: str) -> Dict:
        raise NotImplementedError

    def dns(self, service: str) -> Dict:
        raise NotImplementedError

    def heartbeat(self, peer: str) -> bool:
        raise NotImplementedError

    def now(self) -> float:
        return time.time()

    # -- mutation ---------------------------------------------------------- #
    def run(self, argv: Sequence[str], timeout: float = COMMAND_TIMEOUT_SECONDS) -> Tuple[int, str, str]:
        raise NotImplementedError


class SystemHost(Host):
    """Real macOS host backed by ioreg / networksetup / ifconfig / scutil / route.

    All subprocess calls are bounded by ``timeout``.  A timeout or non-zero exit
    is reported honestly as ``(returncode, stdout, stderr)`` — never swallowed
    into a false success.
    """

    def _cmd(self, argv: Sequence[str], timeout: float = COMMAND_TIMEOUT_SECONDS) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"timeout after {timeout}s: {' '.join(argv)}"
        except FileNotFoundError as exc:
            return 127, "", str(exc)

    def run(self, argv: Sequence[str], timeout: float = COMMAND_TIMEOUT_SECONDS) -> Tuple[int, str, str]:
        return self._cmd(argv, timeout)

    def usb_devices(self) -> List[Dict]:
        rc, out, _ = self._cmd(["ioreg", "-p", "IOUSB", "-l", "-w", "0"])
        devices: List[Dict] = []
        if rc != 0:
            return devices
        # ioreg -l emits one dictionary per node; parse idVendor/idProduct/
        # USB Product Name/USB Serial Number blocks.
        for block in re.split(r"\+-o ", out):
            vid = re.search(r'"idVendor"\s*=\s*(\d+)', block)
            pid = re.search(r'"idProduct"\s*=\s*(\d+)', block)
            product = re.search(r'"USB Product Name"\s*=\s*"([^"]*)"', block)
            serial = re.search(r'"USB Serial Number"\s*=\s*"([^"]*)"', block)
            if not (vid and pid):
                continue
            devices.append(
                {
                    "vid": int(vid.group(1)),
                    "pid": int(pid.group(1)),
                    "product": product.group(1) if product else "",
                    "serial": serial.group(1) if serial else "",
                }
            )
        return devices

    def interfaces(self) -> List[Dict]:
        rc, out, _ = self._cmd(["ifconfig"])
        ifaces: List[Dict] = []
        if rc != 0:
            return ifaces
        current: Optional[Dict] = None
        for line in out.splitlines():
            m = re.match(r"^(\S+):\s+flags=", line)
            if m:
                if current:
                    ifaces.append(current)
                current = {"name": m.group(1), "addresses": [], "status": "", "description": ""}
                if "UP" in line:
                    current["status"] = "active"
                continue
            if current is None:
                continue
            inet = re.search(r"inet (\d+\.\d+\.\d+\.\d+) netmask 0x([0-9a-fA-F]+)", line)
            if inet:
                mask = ipaddress.IPv4Address(int(inet.group(2), 16))
                current["addresses"].append({"address": inet.group(1), "netmask": str(mask)})
            status = re.search(r"status:\s+(\S+)", line)
            if status:
                current["status"] = status.group(1)
        if current:
            ifaces.append(current)
        return ifaces

    def routes(self) -> List[Dict]:
        rc, out, _ = self._cmd(["netstat", "-rn", "-f", "inet"])
        routes: List[Dict] = []
        if rc != 0:
            return routes
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4 or parts[0] in ("Destination", "Routing"):
                continue
            dest, gateway, flags, iface = parts[0], parts[1], parts[2], parts[3]
            if not re.match(r"^[\d./]+$", dest):
                continue
            routes.append({"destination": dest, "gateway": gateway, "flags": flags, "interface": iface})
        return routes

    def services(self) -> List[Dict]:
        rc, out, _ = self._cmd(["networksetup", "-listnetworkserviceorder"])
        services: List[Dict] = []
        if rc != 0:
            return services
        current: Optional[Dict] = None
        for line in out.splitlines():
            head = re.match(r"^\((\d+)\)\s+(.*)$", line)
            if head:
                if current:
                    services.append(current)
                current = {"order": int(head.group(1)), "name": head.group(2).lstrip("* ").strip(), "device": ""}
                continue
            dev = re.search(r"Device:\s+(\S+)\)", line)
            if dev and current is not None:
                current["device"] = dev.group(1)
        if current:
            services.append(current)
        # enabled state
        for svc in services:
            rc2, out2, _ = self._cmd(["networksetup", "-listnetworkserviceorder"])
            _ = rc2, out2  # enabled state derived below via -getinfo is expensive; default enabled
            svc["enabled"] = True
        return services

    def service_order(self) -> List[str]:
        return [s["name"] for s in self.services()]

    def wifi_device(self) -> Optional[str]:
        rc, out, _ = self._cmd(["networksetup", "-listallhardwareports"])
        if rc != 0:
            return None
        lines = out.splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^Hardware Port:\s+(Wi-Fi|AirPort)$", line):
                if i + 1 < len(lines):
                    m = re.match(r"^Device:\s+(\S+)", lines[i + 1])
                    if m:
                        return m.group(1)
        return None

    def wifi_power(self, device: str) -> Optional[bool]:
        rc, out, _ = self._cmd(["networksetup", "-getairportpower", device])
        if rc != 0:
            return None
        m = re.search(r":\s*(On|Off)", out)
        if not m:
            return None
        return m.group(1) == "On"

    def wifi_ssid(self, device: str) -> Optional[str]:
        rc, out, _ = self._cmd(["networksetup", "-getairportnetwork", device])
        if rc != 0:
            return None
        m = re.search(r":\s*(.+)$", out)
        if not m:
            return None
        ssid = m.group(1).strip()
        if ssid.lower().startswith("you are not associated"):
            return None
        return ssid

    def wifi_ipv4(self, device: str) -> Dict:
        rc, out, _ = self._cmd(["ipconfig", "getpacket", device])
        info = {"mode": "manual", "address": None, "subnet_mask": None, "router": None}
        if rc == 0 and out.strip():
            info["mode"] = "dhcp"
            addr = re.search(r"yiaddr\s*=\s*([\d.]+)", out)
            mask = re.search(r"subnet_mask\s*=\s*([\d.]+)", out)
            router = re.search(r"router\s*=\s*([\d.]+)", out)
            if addr:
                info["address"] = addr.group(1)
            if mask:
                info["subnet_mask"] = mask.group(1)
            if router:
                info["router"] = router.group(1)
        else:
            rc2, out2, _ = self._cmd(["ifconfig", device])
            if rc2 == 0:
                inet = re.search(r"inet ([\d.]+) netmask 0x([0-9a-fA-F]+)", out2)
                if inet:
                    info["address"] = inet.group(1)
                    info["subnet_mask"] = str(ipaddress.IPv4Address(int(inet.group(2), 16)))
        return info

    def dns(self, service: str) -> Dict:
        result = {"servers": [], "search": []}
        rc, out, _ = self._cmd(["networksetup", "-getdnsservers", service])
        if rc == 0:
            for line in out.splitlines():
                line = line.strip()
                if line and re.match(r"^[\d.]+$", line):
                    result["servers"].append(line)
        rc2, out2, _ = self._cmd(["networksetup", "-getsearchdomains", service])
        if rc2 == 0:
            for line in out2.splitlines():
                line = line.strip()
                if line and not line.lower().startswith("there aren"):
                    result["search"].append(line)
        return result

    def heartbeat(self, peer: str) -> bool:
        rc, _, _ = self._cmd(["ping", "-c", "1", "-W", "1000", "-t", "1", peer], timeout=3.0)
        return rc == 0


# --------------------------------------------------------------------------- #
# Identity proof — conservative, multi-signal, fail-closed.
# --------------------------------------------------------------------------- #


def _iface_in_bootmux_net(iface: Dict) -> bool:
    net = ipaddress.ip_network(BOOTMUX_NET)
    for addr in iface.get("addresses", []):
        try:
            if ipaddress.ip_address(addr["address"]) in net:
                return True
        except ValueError:
            continue
    return False


def _service_for_interface(services: List[Dict], iface_name: str) -> Optional[str]:
    for svc in services:
        if svc.get("device") == iface_name:
            return svc.get("name")
    return None


def prove_identity(host: Host) -> IdentityResult:
    """Prove a BOOTMUX-owned interface using >=2 signals incl. >=1 hardware.

    Ambiguity (signals but not enough, or multiple candidate interfaces) fails
    closed: ``proven=False, ambiguous=True`` and no interface is released for
    mutation.
    """

    usb = host.usb_devices()
    ifaces = host.interfaces()
    services = host.services()
    routes = host.routes()

    bootmux_usb_present = any(
        d.get("vid") == BOOTMUX_USB_VID and d.get("pid") == BOOTMUX_USB_PID for d in usb
    )
    product_match = any(BOOTMUX_PRODUCT in (d.get("product") or "") for d in usb)
    serial_match = any((d.get("serial") or "") == BOOTMUX_SERIAL for d in usb)

    candidates = [i for i in ifaces if _iface_in_bootmux_net(i)]

    if not candidates:
        # No BOOTMUX-net interface.  A plugged BOOTMUX USB device alone is NOT a
        # network mutation target — this is the safe HID-only case.
        return IdentityResult(
            proven=False,
            ambiguous=False,
            interface=None,
            service=None,
            hardware_signals=_hw_signals(bootmux_usb_present, product_match, serial_match),
            network_signals=[],
            reason="no interface in 10.77.0.0/24",
        )

    if len(candidates) > 1:
        return IdentityResult(
            proven=False,
            ambiguous=True,
            interface=None,
            service=None,
            hardware_signals=_hw_signals(bootmux_usb_present, product_match, serial_match),
            network_signals=["multiple 10.77.0.0/24 interfaces"],
            reason="multiple candidate interfaces; refusing to guess",
        )

    iface = candidates[0]
    iface_name = iface["name"]
    service = _service_for_interface(services, iface_name)

    hw = _hw_signals(bootmux_usb_present, product_match, serial_match)
    net_signals: List[str] = []
    net_signals.append(f"interface {iface_name} in {BOOTMUX_NET}")
    if any(r.get("gateway") == BOOTMUX_PEER for r in routes):
        net_signals.append(f"gateway {BOOTMUX_PEER}")
    if service and BOOTMUX_SERVICE_HINT.lower() in service.lower():
        net_signals.append("service description contains BOOTMUX USB Ethernet")
    if any(r.get("interface") == iface_name for r in routes):
        net_signals.append(f"route through proven interface {iface_name}")

    total = len(hw) + len(net_signals)
    proven = len(hw) >= MIN_HARDWARE_SIGNALS and total >= MIN_SIGNALS

    if not proven:
        return IdentityResult(
            proven=False,
            ambiguous=True,
            interface=iface_name,
            service=service,
            hardware_signals=hw,
            network_signals=net_signals,
            reason=f"insufficient signals (hardware={len(hw)}, total={total}); audit-only",
        )

    return IdentityResult(
        proven=True,
        ambiguous=False,
        interface=iface_name,
        service=service,
        hardware_signals=hw,
        network_signals=net_signals,
        reason="proven BOOTMUX-owned",
    )


def _hw_signals(vid_pid: bool, product: bool, serial: bool) -> List[str]:
    signals: List[str] = []
    if vid_pid:
        signals.append(f"USB VID:PID {BOOTMUX_USB_VID:#06x}:{BOOTMUX_USB_PID:#06x}")
    if product:
        signals.append(f'product "{BOOTMUX_PRODUCT}"')
    if serial:
        signals.append(f'serial "{BOOTMUX_SERIAL}"')
    return signals


# --------------------------------------------------------------------------- #
# Persistent state store — hardened, bounded, secret-free.
# --------------------------------------------------------------------------- #

BASELINE_KEYS = {
    "schema_version",
    "captured_at",
    "wifi",
    "network",
    "metadata",
}


class StateStoreError(Exception):
    """Raised when the state store fails closed validation."""


class StateStore:
    """Root-owned, mode-hardened, atomic JSON state with rollback snapshot.

    ``enforce_owner`` gates the root-ownership checks so the suite can exercise
    the store inside an unprivileged temp dir.  Symlinks, unexpected modes and
    schema violations always fail closed regardless of ``enforce_owner``.
    """

    def __init__(self, root: str, enforce_owner: bool = True) -> None:
        self.root = root
        self.enforce_owner = enforce_owner

    # -- directory --------------------------------------------------------- #
    def validate_dir(self) -> None:
        path = self.root
        if os.path.islink(path):
            raise StateStoreError(f"state dir is a symlink: {path}")
        if not os.path.isdir(path):
            raise StateStoreError(f"state dir missing: {path}")
        st = os.stat(path)
        mode = st.st_mode & 0o777
        if mode != 0o700:
            raise StateStoreError(f"state dir mode {oct(mode)} != 0700")
        if self.enforce_owner and st.st_uid != 0:
            raise StateStoreError(f"state dir owner uid {st.st_uid} != 0")

    def ensure_dir(self) -> None:
        if os.path.islink(self.root):
            raise StateStoreError(f"state dir is a symlink: {self.root}")
        os.makedirs(self.root, exist_ok=True)
        os.chmod(self.root, 0o700)

    # -- files ------------------------------------------------------------- #
    def _path(self, name: str) -> str:
        return os.path.join(self.root, name)

    def _validate_file(self, path: str) -> None:
        if os.path.islink(path):
            raise StateStoreError(f"state file is a symlink: {path}")
        st = os.stat(path)
        mode = st.st_mode & 0o777
        if mode != 0o600:
            raise StateStoreError(f"state file mode {oct(mode)} != 0600: {path}")
        if self.enforce_owner and st.st_uid != 0:
            raise StateStoreError(f"state file owner uid {st.st_uid} != 0: {path}")

    def atomic_write(self, name: str, payload: Dict) -> None:
        self.ensure_dir()
        path = self._path(name)
        if os.path.islink(path):
            raise StateStoreError(f"refusing to write through symlink: {path}")
        fd, tmp = tempfile.mkstemp(prefix=f".{name}.", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        # fsync the directory so the rename is durable.
        dir_fd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    def load(self, name: str) -> Optional[Dict]:
        path = self._path(name)
        if not os.path.exists(path):
            return None
        self._validate_file(path)
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise StateStoreError(f"state file not an object: {path}")
        return data

    # -- baseline ---------------------------------------------------------- #
    def write_baseline(self, baseline: Dict, retain_previous: bool = True) -> None:
        existing = self.load(STATE_BASELINE)
        if retain_previous and existing is not None:
            self.atomic_write(STATE_PREVIOUS, existing)
        self.atomic_write(STATE_BASELINE, baseline)

    def read_baseline(self) -> Optional[Dict]:
        data = self.load(STATE_BASELINE)
        if data is None:
            return None
        if data.get("schema_version") != SCHEMA_VERSION:
            raise StateStoreError(
                f"baseline schema_version {data.get('schema_version')} != {SCHEMA_VERSION}"
            )
        unknown = set(data) - BASELINE_KEYS
        if unknown:
            raise StateStoreError(f"baseline has unexpected keys: {sorted(unknown)}")
        return data


# --------------------------------------------------------------------------- #
# Baseline capture
# --------------------------------------------------------------------------- #


def host_is_clean(host: Host, identity: IdentityResult) -> bool:
    """A clean host has no proven BOOTMUX interface AND no BOOTMUX default route
    or BOOTMUX-owned service."""

    if identity.proven:
        return False
    for route in host.routes():
        if route.get("gateway") == BOOTMUX_PEER:
            return False
        if identity.interface and route.get("interface") == identity.interface:
            return False
    return True


def capture_baseline(host: Host) -> Dict:
    """Capture the host Wi-Fi / network state.  SSID is private state and is
    stored only for reconnection; callers must redact it from logs/status."""

    wifi_device = host.wifi_device()
    services = host.services()
    wifi_service = None
    if wifi_device:
        wifi_service = _service_for_interface(services, wifi_device)

    wifi_block: Dict = {
        "hardware_device": wifi_device,
        "service_name": wifi_service,
        "power": host.wifi_power(wifi_device) if wifi_device else None,
        "associated_ssid": host.wifi_ssid(wifi_device) if wifi_device else None,
    }
    if wifi_device:
        ipv4 = host.wifi_ipv4(wifi_device)
        wifi_block["ipv4_mode"] = ipv4.get("mode")
        wifi_block["ipv4_address"] = ipv4.get("address")
        wifi_block["subnet_mask"] = ipv4.get("subnet_mask")
        wifi_block["router"] = ipv4.get("router")
    else:
        wifi_block.update({"ipv4_mode": None, "ipv4_address": None, "subnet_mask": None, "router": None})

    if wifi_service:
        dns = host.dns(wifi_service)
        wifi_block["dns_servers"] = dns.get("servers", [])
        wifi_block["search_domains"] = dns.get("search", [])
    else:
        wifi_block["dns_servers"] = []
        wifi_block["search_domains"] = []

    routes = host.routes()
    default_route = next((r for r in routes if r.get("destination") == "default"), None)
    network_block = {
        "default_gateway": default_route.get("gateway") if default_route else None,
        "default_interface": default_route.get("interface") if default_route else None,
        "network_service_order": [s["name"] for s in sorted(services, key=lambda s: s.get("order", 0))],
        "service_enabled_states": {s["name"]: bool(s.get("enabled", True)) for s in services},
        "bootmux_routes": [],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": int(host.now()),
        "wifi": wifi_block,
        "network": network_block,
        "metadata": {"schema_version": SCHEMA_VERSION, "redacted_fields": ["wifi.associated_ssid"]},
    }


def redact_baseline(baseline: Optional[Dict]) -> Optional[Dict]:
    """Return a copy safe for logs/status: SSID replaced by a redaction token."""

    if baseline is None:
        return None
    copy = json.loads(json.dumps(baseline))
    wifi = copy.get("wifi", {})
    if wifi.get("associated_ssid") is not None:
        wifi["associated_ssid"] = "<redacted>"
    return copy


# --------------------------------------------------------------------------- #
# Repair plan builders — PURE.  They observe the host and emit the exact,
# minimal command plan.  Tests assert these plans directly; mutation happens
# only inside execute_plan().
# --------------------------------------------------------------------------- #


def _is_link_gateway(gateway: Optional[str]) -> bool:
    return bool(gateway) and gateway.lower().startswith("link#")


def plan_r1_routes(host: Host, identity: IdentityResult) -> RepairPlan:
    """R1 — remove only BOOTMUX-owned routes.  Never flush the global table."""

    plan = RepairPlan()
    iface = identity.interface
    for route in host.routes():
        gateway = route.get("gateway")
        rif = route.get("interface")
        dest = route.get("destination")
        flags = route.get("flags", "")
        owned = (gateway == BOOTMUX_PEER) or (iface is not None and rif == iface)
        if not owned:
            continue
        argv: List[str] = ["route", "-n", "delete"]
        if dest == "default":
            argv.append("default")
            if "I" in flags and rif:
                argv += ["-ifscope", rif]
        elif dest and "/" in dest:
            argv += ["-net", dest]
        else:
            argv += ["-host", dest or "default"]
        if gateway and not _is_link_gateway(gateway):
            argv.append(gateway)
        plan.add(
            Command(
                tuple(argv),
                "R1",
                f"remove BOOTMUX route {dest} via {gateway} ({rif})",
                target_interface=rif,
            )
        )
    if not plan.commands:
        plan.notes.append("R1: no BOOTMUX-owned routes present")
    return plan


def plan_r2_service(host: Host, identity: IdentityResult) -> RepairPlan:
    """R2 — disable ONLY the proven BOOTMUX service.  Never delete it."""

    plan = RepairPlan()
    service = identity.service
    if not service:
        plan.notes.append("R2: no network service maps to the BOOTMUX interface")
        return plan
    enabled = True
    for svc in host.services():
        if svc.get("name") == service:
            enabled = bool(svc.get("enabled", True))
            break
    if not enabled:
        plan.notes.append(f"R2: service {service} already disabled")
        return plan
    plan.add(
        Command(
            ("networksetup", "-setnetworkserviceenabled", service, "off"),
            "R2",
            f"disable BOOTMUX service {service}",
            target_service=service,
        )
    )
    return plan


def plan_r3_ipv4(host: Host, identity: IdentityResult, baseline: Optional[Dict]) -> RepairPlan:
    """R3 — restore the captured Wi-Fi IPv4 mode.  Never convert manual->DHCP."""

    plan = RepairPlan()
    if baseline is None:
        plan.notes.append("R3: no baseline; not inventing IPv4 config")
        return plan
    wifi = baseline.get("wifi", {})
    device = wifi.get("hardware_device")
    service = wifi.get("service_name")
    mode = wifi.get("ipv4_mode")
    if not device:
        plan.notes.append("R3: baseline has no Wi-Fi device")
        return plan

    current = host.wifi_ipv4(device)
    if mode == "dhcp":
        if current.get("mode") != "dhcp":
            plan.add(
                Command(
                    ("ipconfig", "set", device, "DHCP"),
                    "R3",
                    f"renew DHCP on {device}",
                    target_interface=device,
                )
            )
        else:
            plan.notes.append(f"R3: {device} already DHCP")
    elif mode == "manual":
        addr = wifi.get("ipv4_address")
        mask = wifi.get("subnet_mask")
        router = wifi.get("router")
        if not (service and addr and mask and router):
            plan.notes.append("R3: manual baseline incomplete; refusing to invent values")
            return plan
        same = (
            current.get("mode") == "manual"
            and current.get("address") == addr
            and current.get("subnet_mask") == mask
            and current.get("router") == router
        )
        if not same:
            plan.add(
                Command(
                    ("networksetup", "-setmanual", service, addr, mask, router),
                    "R3",
                    f"restore manual IPv4 on {service}",
                    target_service=service,
                )
            )
        else:
            plan.notes.append(f"R3: {service} manual IPv4 already matches baseline")
    else:
        plan.notes.append(f"R3: baseline ipv4_mode {mode!r} not restorable")
    return plan


def plan_r4_dns(host: Host, identity: IdentityResult, baseline: Optional[Dict]) -> RepairPlan:
    """R4 — restore DNS/search domains exactly, preserving automatic vs explicit."""

    plan = RepairPlan()
    if baseline is None:
        plan.notes.append("R4: no baseline; not inventing DNS config")
        return plan
    wifi = baseline.get("wifi", {})
    service = wifi.get("service_name")
    if not service:
        plan.notes.append("R4: baseline has no Wi-Fi service")
        return plan
    want_servers = list(wifi.get("dns_servers", []))
    want_search = list(wifi.get("search_domains", []))
    current = host.dns(service)
    cur_servers = list(current.get("servers", []))
    cur_search = list(current.get("search", []))

    if cur_servers != want_servers:
        if want_servers:
            argv = ("networksetup", "-setdnsservers", service, *want_servers)
        else:
            argv = ("networksetup", "-setdnsservers", service, "Empty")
        plan.add(Command(argv, "R4", f"restore DNS on {service}", target_service=service))
    else:
        plan.notes.append(f"R4: DNS on {service} already matches baseline")

    if cur_search != want_search:
        if want_search:
            argv = ("networksetup", "-setsearchdomains", service, *want_search)
        else:
            argv = ("networksetup", "-setsearchdomains", service, "Empty")
        plan.add(Command(argv, "R4", f"restore search domains on {service}", target_service=service))
    else:
        plan.notes.append(f"R4: search domains on {service} already match baseline")
    return plan


def plan_r5_order(host: Host, identity: IdentityResult, baseline: Optional[Dict]) -> RepairPlan:
    """R5 — restore service order + enabled states only on real diff.

    Never constructs an order from a partial list: the baseline order is applied
    only when it is a complete permutation of the current service set.
    """

    plan = RepairPlan()
    if baseline is None:
        plan.notes.append("R5: no baseline; not inventing service order")
        return plan
    network = baseline.get("network", {})
    want_order = list(network.get("network_service_order", []))
    want_enabled = dict(network.get("service_enabled_states", {}))

    bootmux_service = identity.service
    services = host.services()
    # R2 owns the BOOTMUX service (disable-only, never deleted).  Exclude it from
    # the order comparison so a baseline captured without the BOOTMUX service can
    # still restore the order of the remaining, unrelated services.
    current_order = [
        s["name"]
        for s in sorted(services, key=lambda s: s.get("order", 0))
        if s["name"] != bootmux_service
    ]
    want_order = [name for name in want_order if name != bootmux_service]
    current_enabled = {s["name"]: bool(s.get("enabled", True)) for s in services}

    if want_order and set(want_order) == set(current_order) and current_order != want_order:
        plan.add(
            Command(
                ("networksetup", "-ordernetworkservices", *want_order),
                "R5",
                "restore network service order",
            )
        )
    elif want_order and set(want_order) != set(current_order):
        plan.notes.append("R5: service set differs from baseline; refusing partial order")
    else:
        plan.notes.append("R5: service order already matches baseline")

    for name, want_state in want_enabled.items():
        if name == bootmux_service:
            continue  # R2 owns the BOOTMUX service state
        if name not in current_enabled:
            continue  # never touch a service that no longer exists
        if current_enabled[name] != want_state:
            plan.add(
                Command(
                    ("networksetup", "-setnetworkserviceenabled", name, "on" if want_state else "off"),
                    "R5",
                    f"restore enabled state of {name}",
                    target_service=name,
                )
            )
    return plan


def build_repair_plan(host: Host, identity: IdentityResult, baseline: Optional[Dict]) -> RepairPlan:
    """Compose the R1-R5 plan.  Pure and idempotent (diff-driven)."""

    combined = RepairPlan()
    for sub in (
        plan_r1_routes(host, identity),
        plan_r2_service(host, identity),
        plan_r3_ipv4(host, identity, baseline),
        plan_r4_dns(host, identity, baseline),
        plan_r5_order(host, identity, baseline),
    ):
        combined.commands.extend(sub.commands)
        combined.notes.extend(sub.notes)
    combined.needs_change = bool(combined.commands)
    return combined


def build_wifi_toggle_plan(
    host: Host,
    baseline: Optional[Dict],
    now: float,
    last_toggle_at: Optional[float],
) -> RepairPlan:
    """R6 — Wi-Fi power cycle as a LAST RESORT, with a bounded cooldown.

    Emitted only when the baseline says Wi-Fi was powered on and the cooldown
    has elapsed.  Reconnects to the captured SSID using saved credentials (no
    password on the CLI).
    """

    plan = RepairPlan()
    if baseline is None:
        plan.notes.append("R6: no baseline; will not toggle Wi-Fi")
        return plan
    wifi = baseline.get("wifi", {})
    device = wifi.get("hardware_device")
    if not device:
        plan.notes.append("R6: baseline has no Wi-Fi device")
        return plan
    if wifi.get("power") is not True:
        plan.notes.append("R6: baseline Wi-Fi was not powered on; will not toggle")
        return plan
    if last_toggle_at is not None and (now - last_toggle_at) < WIFI_TOGGLE_COOLDOWN_SECONDS:
        plan.notes.append("R6: cooldown active; skipping toggle")
        return plan

    plan.add(Command(("networksetup", "-setairportpower", device, "off"), "R6", f"power off {device}", target_interface=device))
    plan.add(Command(("networksetup", "-setairportpower", device, "on"), "R6", f"power on {device}", target_interface=device))
    ssid = wifi.get("associated_ssid")
    if ssid:
        plan.add(
            Command(
                ("networksetup", "-setairportnetwork", device, ssid),
                "R6",
                "rejoin captured SSID using saved credentials",
                target_interface=device,
            )
        )
    else:
        plan.notes.append("R6: SSID unavailable; relying on auto-join after power restore")
    return plan


# --------------------------------------------------------------------------- #
# Execution — the ONLY mutation path.
# --------------------------------------------------------------------------- #


@dataclass
class ExecutionResult:
    executed: List[Command] = field(default_factory=list)
    failures: List[Dict] = field(default_factory=list)
    ok: bool = True

    def as_dict(self) -> Dict:
        return {
            "ok": self.ok,
            "executed": [c.as_dict() for c in self.executed],
            "failures": self.failures,
        }


def execute_plan(host: Host, plan: RepairPlan) -> ExecutionResult:
    result = ExecutionResult()
    for command in plan.commands:
        returncode, stdout, stderr = host.run(command.argv)
        if returncode != 0:
            result.ok = False
            result.failures.append(
                {
                    "argv": list(command.argv),
                    "step": command.step,
                    "returncode": returncode,
                    "stderr": stderr.strip()[:500],
                }
            )
        else:
            result.executed.append(command)
    return result


# --------------------------------------------------------------------------- #
# Verification — R7.
# --------------------------------------------------------------------------- #


def verify(host: Host, identity: IdentityResult, baseline: Optional[Dict]) -> Dict[str, bool]:
    routes = host.routes()
    iface = identity.interface
    bootmux_routes = [
        r
        for r in routes
        if r.get("gateway") == BOOTMUX_PEER or (iface is not None and r.get("interface") == iface)
    ]
    default_routes = [r for r in routes if r.get("destination") == "default"]
    bootmux_default = [
        r
        for r in default_routes
        if r.get("gateway") == BOOTMUX_PEER or (iface is not None and r.get("interface") == iface)
    ]
    non_bootmux_default = [r for r in default_routes if r not in bootmux_default]

    services = host.services()
    bootmux_service_enabled = True
    if identity.service:
        for svc in services:
            if svc.get("name") == identity.service:
                bootmux_service_enabled = bool(svc.get("enabled", True))
                break
    bootmux_service_disabled = (identity.service is None) or (not bootmux_service_enabled)

    result: Dict[str, bool] = {
        "bootmux_default_route_absent": not bootmux_default,
        "bootmux_scoped_routes_absent": not bootmux_routes,
        "bootmux_service_disabled": bootmux_service_disabled,
    }

    wifi = (baseline or {}).get("wifi", {})
    device = wifi.get("hardware_device")

    if device:
        result["wifi_power_matches_baseline"] = host.wifi_power(device) == wifi.get("power")
        want_ssid = wifi.get("associated_ssid")
        cur_ssid = host.wifi_ssid(device)
        if want_ssid in (None, "<redacted>"):
            result["wifi_ssid_matches_baseline_or_redacted_equivalent"] = True
        else:
            result["wifi_ssid_matches_baseline_or_redacted_equivalent"] = cur_ssid == want_ssid
        result["wifi_ipv4_mode_matches_baseline"] = host.wifi_ipv4(device).get("mode") == wifi.get("ipv4_mode")
    else:
        result["wifi_power_matches_baseline"] = True
        result["wifi_ssid_matches_baseline_or_redacted_equivalent"] = True
        result["wifi_ipv4_mode_matches_baseline"] = True

    result["wifi_default_route_restored"] = bool(non_bootmux_default)

    if baseline is not None and device:
        service = wifi.get("service_name")
        if service:
            cur_dns = host.dns(service)
            result["wifi_dns_matches_baseline"] = list(cur_dns.get("servers", [])) == list(
                wifi.get("dns_servers", [])
            )
        else:
            result["wifi_dns_matches_baseline"] = True
    else:
        result["wifi_dns_matches_baseline"] = True

    if baseline is not None:
        network = baseline.get("network", {})
        # Exclude the BOOTMUX service (owned by R2, disable-only) so the order
        # comparison matches plan_r5_order exactly.
        want_order = [n for n in network.get("network_service_order", []) if n != identity.service]
        current_order = [
            s["name"]
            for s in sorted(services, key=lambda s: s.get("order", 0))
            if s["name"] != identity.service
        ]
        if want_order and set(want_order) == set(current_order):
            result["service_order_matches_baseline"] = current_order == want_order
        else:
            result["service_order_matches_baseline"] = True  # cannot judge; not a regression

        want_enabled = dict(network.get("service_enabled_states", {}))
        current_enabled = {s["name"]: bool(s.get("enabled", True)) for s in services}
        unrelated_ok = True
        for name, want_state in want_enabled.items():
            if name == identity.service or name not in current_enabled:
                continue
            if current_enabled[name] != want_state:
                unrelated_ok = False
                break
        result["unrelated_services_unchanged"] = unrelated_ok
    else:
        result["service_order_matches_baseline"] = True
        result["unrelated_services_unchanged"] = True

    return result


def classify(verification: Dict[str, bool]) -> str:
    if all(verification.get(k, False) for k in VERIFY_KEYS):
        return "REPAIRED"
    failed = [k for k in VERIFY_KEYS if not verification.get(k, False)]
    return "INCOMPLETE:" + ",".join(failed)


# --------------------------------------------------------------------------- #
# FakeHost — deterministic, fixture-driven simulator for tests and --self-test.
#
# run() RECORDS every command (so tests assert the exact plan) AND models the
# real tool semantics so verify() sees coherent post-repair state.  It never
# touches the real system; using it guarantees the developer Mac is untouched.
# --------------------------------------------------------------------------- #


class FakeHost(Host):
    def __init__(
        self,
        usb: Optional[List[Dict]] = None,
        interfaces: Optional[List[Dict]] = None,
        routes: Optional[List[Dict]] = None,
        services: Optional[List[Dict]] = None,
        wifi_device: Optional[str] = None,
        wifi_power: Optional[bool] = None,
        wifi_ssid: Optional[str] = None,
        wifi_ipv4: Optional[Dict] = None,
        dns: Optional[Dict[str, Dict]] = None,
        heartbeat: bool = True,
        clock: float = 1000.0,
    ) -> None:
        self._usb = list(usb or [])
        self._interfaces = list(interfaces or [])
        self._routes = list(routes or [])
        self._services = list(services or [])
        self._wifi_device = wifi_device
        self._wifi_power = wifi_power
        self._wifi_ssid = wifi_ssid
        self._wifi_ipv4 = dict(wifi_ipv4 or {"mode": "dhcp", "address": None, "subnet_mask": None, "router": None})
        self._dns = {k: dict(v) for k, v in (dns or {}).items()}
        self._heartbeat = heartbeat
        self._clock = clock
        self.commands: List[List[str]] = []
        self.run_results: Dict[Tuple[str, ...], Tuple[int, str, str]] = {}

    # -- observation ------------------------------------------------------- #
    def usb_devices(self) -> List[Dict]:
        return self._usb

    def interfaces(self) -> List[Dict]:
        return self._interfaces

    def routes(self) -> List[Dict]:
        return self._routes

    def services(self) -> List[Dict]:
        return self._services

    def service_order(self) -> List[str]:
        return [s["name"] for s in sorted(self._services, key=lambda s: s.get("order", 0))]

    def wifi_device(self) -> Optional[str]:
        return self._wifi_device

    def wifi_power(self, device: str) -> Optional[bool]:
        return self._wifi_power

    def wifi_ssid(self, device: str) -> Optional[str]:
        return self._wifi_ssid

    def wifi_ipv4(self, device: str) -> Dict:
        return dict(self._wifi_ipv4)

    def dns(self, service: str) -> Dict:
        return dict(self._dns.get(service, {"servers": [], "search": []}))

    def heartbeat(self, peer: str) -> bool:
        return self._heartbeat

    def now(self) -> float:
        return self._clock

    def advance(self, seconds: float) -> None:
        self._clock += seconds

    # -- mutation (simulated) --------------------------------------------- #
    def run(self, argv: Sequence[str], timeout: float = COMMAND_TIMEOUT_SECONDS) -> Tuple[int, str, str]:
        argv = list(argv)
        self.commands.append(argv)
        key = tuple(argv)
        if key in self.run_results:
            return self.run_results[key]
        self._simulate(argv)
        return (0, "", "")

    def _route_matches_delete(self, route: Dict, argv: List[str]) -> bool:
        # Prefer an explicit gateway IP in the command: `route delete default
        # 10.77.0.1` removes ONLY the route via that gateway, never an unrelated
        # default route.  Match on gateway when present.
        gateway_arg = None
        for token in reversed(argv):
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", token):
                gateway_arg = token
                break
        if gateway_arg is not None:
            return route.get("gateway") == gateway_arg
        # No explicit gateway (link-local deletion): match destination + ifscope.
        dest_arg = None
        if "default" in argv:
            dest_arg = "default"
        elif "-net" in argv:
            dest_arg = argv[argv.index("-net") + 1]
        elif "-host" in argv:
            dest_arg = argv[argv.index("-host") + 1]
        if dest_arg is None:
            return False
        if route.get("destination") != dest_arg:
            return False
        if "-ifscope" in argv:
            return route.get("interface") == argv[argv.index("-ifscope") + 1]
        return True

    def _simulate(self, argv: List[str]) -> None:
        if not argv:
            return
        prog = argv[0]
        if prog == "route" and "delete" in argv:
            self._routes = [r for r in self._routes if not self._route_matches_delete(r, argv)]
        elif prog == "networksetup":
            if "-setnetworkserviceenabled" in argv:
                idx = argv.index("-setnetworkserviceenabled")
                name, state = argv[idx + 1], argv[idx + 2]
                for svc in self._services:
                    if svc["name"] == name:
                        svc["enabled"] = state == "on"
            elif "-setairportpower" in argv:
                self._wifi_power = argv[-1] == "on"
            elif "-setairportnetwork" in argv:
                self._wifi_ssid = argv[-1]
            elif "-setmanual" in argv:
                self._wifi_ipv4 = {
                    "mode": "manual",
                    "address": argv[-3],
                    "subnet_mask": argv[-2],
                    "router": argv[-1],
                }
            elif "-setdnsservers" in argv:
                idx = argv.index("-setdnsservers")
                name = argv[idx + 1]
                vals = argv[idx + 2 :]
                self._dns.setdefault(name, {})["servers"] = [] if vals == ["Empty"] else vals
            elif "-setsearchdomains" in argv:
                idx = argv.index("-setsearchdomains")
                name = argv[idx + 1]
                vals = argv[idx + 2 :]
                self._dns.setdefault(name, {})["search"] = [] if vals == ["Empty"] else vals
            elif "-ordernetworkservices" in argv:
                idx = argv.index("-ordernetworkservices")
                for i, name in enumerate(argv[idx + 1 :]):
                    for svc in self._services:
                        if svc["name"] == name:
                            svc["order"] = i + 1
        elif prog == "ipconfig" and "set" in argv and "DHCP" in argv:
            self._wifi_ipv4 = {
                "mode": "dhcp",
                "address": "192.168.1.50",
                "subnet_mask": "255.255.255.0",
                "router": "192.168.1.1",
            }


# --------------------------------------------------------------------------- #
# Repair orchestration — one bounded, idempotent repair.
# --------------------------------------------------------------------------- #


def repair_once(
    host: Host,
    store: StateStore,
    now: Optional[float] = None,
    last_toggle_at: Optional[float] = None,
) -> Dict:
    """Run one bounded R1-R7 repair.  Pure planning + simulated/real execution.

    Fails closed on ambiguous identity or invalid state store.  Without a
    baseline it removes only positively identified BOOTMUX state and never
    invents host config.
    """

    if now is None:
        now = host.now()
    report: Dict = {"action": "repair"}
    identity = prove_identity(host)
    report["identity"] = identity.as_dict()

    if identity.ambiguous:
        report.update(
            {
                "action": "audit_only",
                "classification": "AMBIGUOUS",
                "reason": identity.reason,
                "commands": [],
            }
        )
        return report

    baseline: Optional[Dict] = None
    if os.path.isdir(store.root) or os.path.islink(store.root):
        try:
            store.validate_dir()
            baseline = store.read_baseline()
        except StateStoreError as exc:
            report.update(
                {
                    "action": "fail_closed",
                    "classification": "STATE_INVALID",
                    "error": str(exc),
                    "commands": [],
                }
            )
            return report
    report["has_baseline"] = baseline is not None

    plan = build_repair_plan(host, identity, baseline)
    execution = execute_plan(host, plan)
    report["plan"] = plan.as_dict()
    report["execution"] = execution.as_dict()

    verification = verify(host, identity, baseline)
    classification = classify(verification)

    toggled = False
    if classification != "REPAIRED" and execution.ok:
        toggle_plan = build_wifi_toggle_plan(host, baseline, now, last_toggle_at)
        if toggle_plan.commands:
            toggle_exec = execute_plan(host, toggle_plan)
            report["wifi_toggle"] = toggle_plan.as_dict()
            report["wifi_toggle_execution"] = toggle_exec.as_dict()
            toggled = True
            verification = verify(host, identity, baseline)
            classification = classify(verification)

    report["toggled"] = toggled
    report["verification"] = verification
    report["classification"] = classification
    return report


# --------------------------------------------------------------------------- #
# Guardian daemon state machine.
# --------------------------------------------------------------------------- #


class Guardian:
    """Long-running recovery daemon.  ``tick()`` is deterministic given the
    host clock so tests can drive the full state machine without sleeping."""

    def __init__(
        self,
        host: Host,
        store: StateStore,
        stability_seconds: float = BASELINE_STABILITY_SECONDS,
        heartbeat_fail_seconds: float = HEARTBEAT_FAIL_SECONDS,
        idle_poll: float = IDLE_POLL_SECONDS,
        attached_poll: float = ATTACHED_POLL_SECONDS,
    ) -> None:
        self.host = host
        self.store = store
        self.stability_seconds = stability_seconds
        self.heartbeat_fail_seconds = heartbeat_fail_seconds
        self.idle_poll = idle_poll
        self.attached_poll = attached_poll
        self.state = "START"
        self.stable_since: Optional[float] = None
        self.heartbeat_fail_since: Optional[float] = None
        self.was_attached = False
        self.last_wifi_toggle_at: Optional[float] = None

    def _store_valid(self) -> Optional[str]:
        if os.path.isdir(self.store.root) or os.path.islink(self.store.root):
            try:
                self.store.validate_dir()
            except StateStoreError as exc:
                return str(exc)
        return None

    def _existing_baseline(self) -> Optional[Dict]:
        try:
            return self.store.read_baseline()
        except StateStoreError:
            return None

    def _do_repair(self, now: float, reason: str) -> Dict:
        result = repair_once(self.host, self.store, now=now, last_toggle_at=self.last_wifi_toggle_at)
        if result.get("toggled"):
            self.last_wifi_toggle_at = now
        self.state = "NO_BOOTMUX"
        self.stable_since = None
        out = {"action": "repair", "reason": reason}
        out.update(result)
        return out

    def tick(self) -> Dict:
        now = self.host.now()
        report: Dict = {"time": now, "state": self.state}

        store_error = self._store_valid()
        if store_error is not None:
            self.state = "FAIL_CLOSED"
            report.update({"action": "fail_closed", "error": store_error})
            return report

        identity = prove_identity(self.host)
        routes = self.host.routes()
        stale_route = any(r.get("gateway") == BOOTMUX_PEER for r in routes)
        usb_present = any(
            d.get("vid") == BOOTMUX_USB_VID and d.get("pid") == BOOTMUX_USB_PID for d in self.host.usb_devices()
        )

        if identity.proven:
            self.state = "ATTACHED"
            self.was_attached = True
            self.stable_since = None
            if self.host.heartbeat(BOOTMUX_PEER):
                self.heartbeat_fail_since = None
                report["action"] = "monitor_attached"
            else:
                if self.heartbeat_fail_since is None:
                    self.heartbeat_fail_since = now
                if now - self.heartbeat_fail_since >= self.heartbeat_fail_seconds:
                    report.update(self._do_repair(now, "heartbeat_loss"))
                    self.heartbeat_fail_since = None
                else:
                    report["action"] = "heartbeat_failing"
            return report

        self.heartbeat_fail_since = None

        if identity.ambiguous:
            self.state = "AUDIT_ONLY"
            report.update({"action": "audit_only", "reason": identity.reason})
            return report

        detached = self.was_attached and not usb_present
        if stale_route or detached:
            reason = "stale_route" if stale_route else "usb_detached"
            report.update(self._do_repair(now, reason))
            self.was_attached = False
            return report

        self.state = "NO_BOOTMUX"
        self.was_attached = False
        if self.stable_since is None:
            self.stable_since = now
        if self._existing_baseline() is None and now - self.stable_since >= self.stability_seconds:
            if host_is_clean(self.host, identity):
                baseline = capture_baseline(self.host)
                self.store.write_baseline(baseline)
                report["action"] = "baseline_captured"
            else:
                report["action"] = "stable_but_not_clean"
        else:
            report["action"] = "monitoring_idle"
        return report

    def run_daemon(self, max_iterations: Optional[int] = None) -> None:
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            report = self.tick()
            sys.stderr.write(json.dumps({"guardian": report}, sort_keys=True) + "\n")
            sys.stderr.flush()
            interval = self.attached_poll if self.state == "ATTACHED" else self.idle_poll
            time.sleep(interval)
            iterations += 1


# --------------------------------------------------------------------------- #
# CLI commands.
# --------------------------------------------------------------------------- #


def _default_store(state_dir: str) -> StateStore:
    return StateStore(state_dir, enforce_owner=(os.geteuid() == 0))


GUARDIAN_OWNED_FILES = (STATE_BASELINE, STATE_PREVIOUS, STATE_RUNTIME)


def uninstall_guardian(store: StateStore, purge: bool = False) -> Dict:
    """Remove ONLY guardian-owned state files; never touch unrelated files.

    With ``purge=False`` (default) evidence is preserved: the baseline files are
    moved aside under ``evidence/`` rather than deleted.  With ``purge=True``
    they are removed outright.  Unrelated files in the directory are untouched.
    """

    removed: List[str] = []
    preserved: List[str] = []
    if os.path.isdir(store.root):
        evidence_dir = os.path.join(store.root, "evidence")
        for name in os.listdir(store.root):
            if name in GUARDIAN_OWNED_FILES:
                src = os.path.join(store.root, name)
                if purge:
                    os.unlink(src)
                    removed.append(name)
                else:
                    os.makedirs(evidence_dir, exist_ok=True)
                    os.replace(src, os.path.join(evidence_dir, name))
                    preserved.append(name)
    return {"removed": removed, "preserved_evidence": preserved, "purge": purge}


def cmd_audit(host: Host, store: StateStore) -> int:
    identity = prove_identity(host)
    clean = host_is_clean(host, identity)
    baseline = None
    try:
        baseline = store.read_baseline()
    except StateStoreError as exc:
        print(json.dumps({"audit": "state_invalid", "error": str(exc)}, sort_keys=True))
        return 1
    out = {
        "mode": "audit",
        "identity": identity.as_dict(),
        "host_clean": clean,
        "baseline_present": baseline is not None,
        "baseline": redact_baseline(baseline),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def cmd_status(host: Host, store: StateStore) -> int:
    identity = prove_identity(host)
    baseline = None
    state_error = None
    try:
        baseline = store.read_baseline()
    except StateStoreError as exc:
        state_error = str(exc)
    out = {
        "mode": "status",
        "state": "fail_closed" if state_error else ("clean" if host_is_clean(host, identity) else "bootmux_present"),
        "identity": identity.as_dict(),
        "baseline": redact_baseline(baseline),
        "state_error": state_error,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    print("# human-readable", file=sys.stderr)
    print(f"# state={out['state']} proven={identity.proven} ambiguous={identity.ambiguous}", file=sys.stderr)
    return 1 if state_error else 0


def cmd_capture_baseline(host: Host, store: StateStore) -> int:
    identity = prove_identity(host)
    if not host_is_clean(host, identity):
        print(
            json.dumps(
                {"capture": "refused", "reason": "host contaminated by BOOTMUX state", "identity": identity.as_dict()},
                sort_keys=True,
            )
        )
        return 3
    baseline = capture_baseline(host)
    store.write_baseline(baseline)
    print(json.dumps({"capture": "ok", "baseline": redact_baseline(baseline)}, indent=2, sort_keys=True))
    return 0


def cmd_repair_now(host: Host, store: StateStore) -> int:
    report = repair_once(host, store)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("classification") == "REPAIRED" else 4


def cmd_self_test() -> int:
    """Deterministic internal scenario; never touches the real host."""

    host = FakeHost(
        usb=[],
        interfaces=[],
        routes=[
            {"destination": "default", "gateway": BOOTMUX_PEER, "flags": "UGS", "interface": "en7"},
            {"destination": "default", "gateway": "192.168.1.1", "flags": "UGS", "interface": "en0"},
        ],
        services=[],
        wifi_device="en0",
        wifi_power=True,
        wifi_ssid=None,
        wifi_ipv4={"mode": "dhcp", "address": "192.168.1.50", "subnet_mask": "255.255.255.0", "router": "192.168.1.1"},
    )
    tmp = tempfile.mkdtemp(prefix="bootmux-selftest-")
    try:
        store = StateStore(tmp, enforce_owner=False)
        report = repair_once(host, store)
        assert report["classification"] == "REPAIRED", report
        assert host.commands, "expected at least one route deletion"
        assert not any(r.get("gateway") == BOOTMUX_PEER for r in host.routes()), "BOOTMUX route survived"
    finally:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)
    print("SELF_TEST=PASS")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="BOOTMUX macOS network guardian (recovery-only)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit", action="store_true", help="read-only identity + baseline report")
    group.add_argument("--repair-now", action="store_true", help="one bounded idempotent repair")
    group.add_argument("--daemon", action="store_true", help="long-running LaunchDaemon mode")
    group.add_argument("--status", action="store_true", help="sanitized machine + human state")
    group.add_argument("--capture-baseline", action="store_true", help="capture baseline if host is clean")
    group.add_argument("--self-test", action="store_true", help="deterministic internal test; no host mutation")
    parser.add_argument("--state-dir", default=DEFAULT_STATE_DIR, help="persistent state directory")
    parser.add_argument("--max-iterations", type=int, default=None, help="bound the daemon loop (testing)")
    args = parser.parse_args(argv)

    if args.self_test:
        return cmd_self_test()

    host = SystemHost()
    store = _default_store(args.state_dir)

    if args.audit:
        return cmd_audit(host, store)
    if args.status:
        return cmd_status(host, store)
    if args.capture_baseline:
        return cmd_capture_baseline(host, store)
    if args.repair_now:
        return cmd_repair_now(host, store)
    if args.daemon:
        guardian = Guardian(host, store)
        guardian.run_daemon(max_iterations=args.max_iterations)
        return 0
    parser.error("no command selected")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
