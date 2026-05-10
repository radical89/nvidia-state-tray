#!/usr/bin/env python3
"""nvidia-state-tray — NVIDIA GPU state indicator for the system tray."""

import subprocess
from pathlib import Path


def read_power_state(pci_address: str, sysfs_base: str = "/sys/bus/pci/devices") -> str:
    """Read GPU power state from sysfs. Returns 'D3cold', 'D0', etc., or 'error'."""
    path = Path(sysfs_base) / pci_address / "power_state"
    try:
        return path.read_text().strip()
    except (FileNotFoundError, PermissionError):
        return "error"


def find_nvidia_pci_address(sysfs_base: str = "/sys/bus/pci/devices") -> str | None:
    """Scan sysfs for an NVIDIA VGA device. Returns PCI address string or None."""
    devices = Path(sysfs_base)
    for dev in sorted(devices.iterdir()):
        try:
            vendor = (dev / "vendor").read_text().strip()
            cls = (dev / "class").read_text().strip()
            if vendor == "0x10de" and cls.startswith("0x0300"):
                return dev.name
        except (FileNotFoundError, PermissionError):
            continue
    return None


def read_power_draw() -> float | None:
    """Query nvidia-smi for current power draw in watts. Returns None on any failure."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        val = result.stdout.strip().split("\n")[0].strip()
        if not val or val == "[N/A]":
            return None
        return float(val)
    except (subprocess.SubprocessError, ValueError, OSError):
        return None
