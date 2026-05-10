#!/usr/bin/env python3
"""nvidia-state-tray — NVIDIA GPU state indicator for the system tray."""

import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication


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


ICON_SIZE = 22
COLOR_COLD = QColor("#4A90D9")    # blue — D3cold / iGPU only
COLOR_ACTIVE = QColor("#4CAF50")  # green — dGPU active
COLOR_ERROR = QColor("#888888")   # grey — path not found


def make_icon(color: QColor, label: str = "") -> QIcon:
    """Draw a 22×22 rounded-rect icon in the given colour with optional centred white label."""
    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(QColor(0, 0, 0, 0))  # transparent background
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(QColor(0, 0, 0, 60))
    painter.drawRoundedRect(1, 1, ICON_SIZE - 2, ICON_SIZE - 2, 4, 4)
    if label:
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPixelSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, label)
    painter.end()
    return QIcon(pixmap)
