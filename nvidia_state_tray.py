#!/usr/bin/env python3
"""nvidia-state-tray — NVIDIA GPU state indicator for the system tray."""

import argparse
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


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

POLL_FAST_MS = 3_000   # GPU is actively working
POLL_IDLE_MS = 15_000  # GPU is off or low-power — give driver room to enter D3cold
IDLE_WATTS_THRESHOLD = 8.0


def next_poll_ms(state: str, watts: float | None, fast_ms: int = POLL_FAST_MS) -> int:
    """Return the next poll interval based on GPU state.

    Backs off to POLL_IDLE_MS when the GPU is off or drawing low power so the
    NVIDIA driver's idle timer can fire and transition the device to D3cold.
    Frequent nvidia-smi calls reset that timer and prevent the transition.
    """
    if state in ("D3cold", "error"):
        return POLL_IDLE_MS
    if watts is None or watts <= IDLE_WATTS_THRESHOLD:
        return POLL_IDLE_MS
    return fast_ms


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


class GpuStateTray:
    def __init__(self, pci_address: str, interval_ms: int = POLL_FAST_MS) -> None:
        self.pci_address = pci_address
        self.fast_ms = interval_ms
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.tray = QSystemTrayIcon()
        menu = QMenu()
        menu.addAction("Quit", self.app.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._update)
        self._update()

    def _update(self) -> None:
        state = read_power_state(self.pci_address)
        watts = None
        if state == "error":
            self.tray.setIcon(make_icon(COLOR_ERROR, "?"))
            self.tray.setToolTip(f"RTX 5080 — sysfs path not found ({self.pci_address})")
        elif state == "D3cold":
            self.tray.setIcon(make_icon(COLOR_COLD))
            self.tray.setToolTip("RTX 5080 — D3cold (powered off)")
        else:
            watts = read_power_draw()
            label = f"{int(watts)}W" if watts is not None else "?W"
            tooltip_watts = f"{watts:.1f} W" if watts is not None else "unknown"
            self.tray.setIcon(make_icon(COLOR_ACTIVE, label))
            self.tray.setToolTip(f"RTX 5080 — Active · {tooltip_watts}")
        self.timer.start(next_poll_ms(state, watts, self.fast_ms))

    def run(self) -> int:
        return self.app.exec()


def main() -> None:
    parser = argparse.ArgumentParser(description="NVIDIA GPU state system tray indicator")
    parser.add_argument(
        "--pci-address", default=None,
        help="PCI address of the GPU, e.g. 0000:02:00.0 (auto-detected if omitted)",
    )
    parser.add_argument(
        "--interval", type=int, default=3,
        help="Poll interval in seconds (default: 3)",
    )
    args = parser.parse_args()

    pci_address = args.pci_address or find_nvidia_pci_address()
    if not pci_address:
        print("Error: could not find an NVIDIA GPU. Use --pci-address.", file=sys.stderr)
        sys.exit(1)

    tray = GpuStateTray(pci_address, interval_ms=args.interval * 1000)
    sys.exit(tray.run())


if __name__ == "__main__":
    main()
