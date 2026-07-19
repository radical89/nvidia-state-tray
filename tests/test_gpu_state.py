# tests/test_gpu_state.py
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from nvidia_state_tray import (
    COLOR_ACTIVE,
    COLOR_COLD,
    COLOR_ERROR,
    IDLE_WATTS_THRESHOLD,
    MEM_LOCK_CLOCK_MHZ,
    POLL_FAST_MS,
    POLL_IDLE_MS,
    find_nvidia_pci_address,
    make_icon,
    next_poll_ms,
    read_power_draw,
    read_power_state,
    set_mem_clock_lock,
)


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


def test_read_power_draw_returns_float():
    mock = MagicMock()
    mock.stdout = "15.36\n"
    with patch("nvidia_state_tray.subprocess.run", return_value=mock):
        assert read_power_draw() == pytest.approx(15.36)


def test_read_power_draw_na_returns_none():
    mock = MagicMock()
    mock.stdout = "[N/A]\n"
    with patch("nvidia_state_tray.subprocess.run", return_value=mock):
        assert read_power_draw() is None


def test_read_power_draw_empty_returns_none():
    mock = MagicMock()
    mock.stdout = "\n"
    with patch("nvidia_state_tray.subprocess.run", return_value=mock):
        assert read_power_draw() is None


def test_read_power_draw_smi_missing():
    with patch("nvidia_state_tray.subprocess.run", side_effect=FileNotFoundError):
        assert read_power_draw() is None


def test_read_power_draw_timeout():
    with patch("nvidia_state_tray.subprocess.run",
               side_effect=subprocess.TimeoutExpired("nvidia-smi", 2)):
        assert read_power_draw() is None


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication(sys.argv)


def test_make_icon_cold_returns_qicon(qapp):
    icon = make_icon(COLOR_COLD)
    assert isinstance(icon, QIcon)
    assert not icon.isNull()


def test_make_icon_active_with_label(qapp):
    icon = make_icon(COLOR_ACTIVE, "15W")
    assert isinstance(icon, QIcon)
    assert not icon.isNull()


def test_make_icon_error_state(qapp):
    icon = make_icon(COLOR_ERROR, "?")
    assert isinstance(icon, QIcon)
    assert not icon.isNull()


def test_next_poll_d3cold_returns_idle():
    assert next_poll_ms("D3cold", None) == POLL_IDLE_MS


def test_next_poll_error_returns_idle():
    assert next_poll_ms("error", None) == POLL_IDLE_MS


def test_next_poll_high_watts_returns_fast():
    assert next_poll_ms("D0", IDLE_WATTS_THRESHOLD + 1) == POLL_FAST_MS


def test_next_poll_low_watts_returns_idle():
    assert next_poll_ms("D0", IDLE_WATTS_THRESHOLD) == POLL_IDLE_MS


def test_next_poll_none_watts_returns_idle():
    assert next_poll_ms("D0", None) == POLL_IDLE_MS


def test_set_mem_clock_lock_enable_runs_lmc():
    mock = MagicMock()
    mock.returncode = 0
    with patch("nvidia_state_tray.subprocess.run", return_value=mock) as run:
        assert set_mem_clock_lock(True) is True
    cmd = run.call_args.args[0]
    assert cmd[:3] == ["sudo", "-n", "nvidia-smi"]
    assert "-lmc" in cmd
    assert f"{MEM_LOCK_CLOCK_MHZ},{MEM_LOCK_CLOCK_MHZ}" in cmd


def test_set_mem_clock_lock_disable_runs_rmc():
    mock = MagicMock()
    mock.returncode = 0
    with patch("nvidia_state_tray.subprocess.run", return_value=mock) as run:
        assert set_mem_clock_lock(False) is True
    cmd = run.call_args.args[0]
    assert cmd[:3] == ["sudo", "-n", "nvidia-smi"]
    assert "-rmc" in cmd
    assert "-lmc" not in cmd


def test_set_mem_clock_lock_nonzero_exit_returns_false():
    mock = MagicMock()
    mock.returncode = 1
    with patch("nvidia_state_tray.subprocess.run", return_value=mock):
        assert set_mem_clock_lock(True) is False


def test_set_mem_clock_lock_sudo_missing_returns_false():
    with patch("nvidia_state_tray.subprocess.run", side_effect=FileNotFoundError):
        assert set_mem_clock_lock(True) is False


def test_set_mem_clock_lock_timeout_returns_false():
    with patch("nvidia_state_tray.subprocess.run",
               side_effect=subprocess.TimeoutExpired("nvidia-smi", 5)):
        assert set_mem_clock_lock(False) is False
