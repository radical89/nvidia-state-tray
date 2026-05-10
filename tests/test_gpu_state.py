# tests/test_gpu_state.py
import pytest
from nvidia_state_tray import find_nvidia_pci_address, read_power_state


def test_read_power_state_d3cold(tmp_path):
    dev = tmp_path / "0000:02:00.0"
    dev.mkdir()
    (dev / "power_state").write_text("D3cold\n")
    assert read_power_state("0000:02:00.0", sysfs_base=str(tmp_path)) == "D3cold"


def test_read_power_state_d0(tmp_path):
    dev = tmp_path / "0000:02:00.0"
    dev.mkdir()
    (dev / "power_state").write_text("D0\n")
    assert read_power_state("0000:02:00.0", sysfs_base=str(tmp_path)) == "D0"


def test_read_power_state_missing_path(tmp_path):
    assert read_power_state("0000:99:00.0", sysfs_base=str(tmp_path)) == "error"


def test_find_nvidia_pci_address_found(tmp_path):
    dev = tmp_path / "0000:02:00.0"
    dev.mkdir()
    (dev / "vendor").write_text("0x10de\n")
    (dev / "class").write_text("0x030000\n")
    assert find_nvidia_pci_address(sysfs_base=str(tmp_path)) == "0000:02:00.0"


def test_find_nvidia_pci_address_not_found(tmp_path):
    dev = tmp_path / "0000:00:00.0"
    dev.mkdir()
    (dev / "vendor").write_text("0x8086\n")
    (dev / "class").write_text("0x030000\n")
    assert find_nvidia_pci_address(sysfs_base=str(tmp_path)) is None
