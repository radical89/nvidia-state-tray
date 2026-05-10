#!/usr/bin/env python3
"""nvidia-state-tray — NVIDIA GPU state indicator for the system tray."""

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
