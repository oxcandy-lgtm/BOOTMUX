#!/usr/bin/env python3
"""
network-audit.py - Read-only network state audit tool.
NO mutations. Only uses: ifconfig, route, networksetup -list*, networksetup -get*.
"""
import subprocess
import json
import sys

def run(cmd):
    """Run a command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    return result.stdout.strip()

def audit():
    """Collect read-only network state."""
    state = {
        "default_route": run("route -n get default"),
        "interfaces": run("ifconfig -l"),
        "network_services": run("networksetup -listallnetworkservices"),
        "hardware_ports": run("networksetup -listallhardwareports"),
    }
    print(json.dumps(state, indent=2))

if __name__ == "__main__":
    audit()
