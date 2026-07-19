# nvidia-state-tray

A lightweight system tray indicator for Linux showing whether your NVIDIA GPU is powered off or active, with live watt display when running.

| State | Icon | Meaning |
|---|---|---|
| D3cold | Blue | GPU fully powered off — system running on iGPU only |
| Active | Green + watts | GPU awake, e.g. `15W` |
| Error | Grey `?` | GPU not found at expected PCI address |

Built for Optimus laptops (Intel iGPU + NVIDIA dGPU) where the discrete GPU should power down during everyday use and only wake for gaming or compute workloads.

## Requirements

- Linux, KDE Plasma 6 (or any desktop supporting StatusNotifierItem)
- Python 3.8+
- PyQt6 — `python-pyqt6` (Arch/CachyOS) or `python3-pyqt6` (Debian/Ubuntu)
- NVIDIA drivers with `nvidia-smi` in PATH
- NVIDIA Runtime D3 (RTD3) enabled (`DynamicPowerManagement: 2`)

### Verify RTD3 is enabled

```bash
cat /proc/driver/nvidia/params | grep DynamicPower
# Should show: DynamicPowerManagement: 2

cat /sys/bus/pci/devices/0000:02:00.0/power_state
# D3cold = GPU off, D0 = GPU active
```

If RTD3 is not enabled, see the [NVIDIA dynamic power management docs](https://download.nvidia.com/XFree86/Linux-x86_64/595.71.05/README/dynamicpowermanagement.html).

## Install

```bash
git clone https://github.com/radical89/nvidia-state-tray.git
cd nvidia-state-tray
pip install PyQt6   # if not already installed
bash install.sh
```

The icon will appear in your system tray within a few seconds.

## Uninstall

```bash
bash uninstall.sh
```

## Memory-clock lock (anti-stutter)

Right-click the tray icon → **Lock mem clock (anti-stutter)** pins the GPU
memory clock at 14001 MHz. On this driver every memory-clock switch stalls
the whole machine for ~4–5 ms ([open-gpu-kernel-modules#1248]); pinning the
clock stops audio blips and frame hitches while gaming. Unlock when done —
a pinned memory clock raises idle power draw.

Requires a passwordless sudo rule (edit the user as needed):

```bash
echo 'karlos ALL=(root) NOPASSWD: /usr/bin/nvidia-smi -lmc 14001\,14001, /usr/bin/nvidia-smi -rmc' | sudo tee /etc/sudoers.d/nvidia-mem-lock
sudo chmod 440 /etc/sudoers.d/nvidia-mem-lock
sudo visudo -c
```

[open-gpu-kernel-modules#1248]: https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1248

## Manual usage

```bash
# Auto-detect GPU PCI address, poll every 3 seconds
python nvidia_state_tray.py

# Specify PCI address manually
python nvidia_state_tray.py --pci-address 0000:02:00.0

# Change poll interval
python nvidia_state_tray.py --interval 5
```

## How it works

Every 3 seconds the script reads `/sys/bus/pci/devices/<pci>/power_state` directly from sysfs. This is an instantaneous kernel file read — it does **not** wake the GPU. If the state is `D3cold`, the GPU is fully powered off and the icon is blue. Otherwise `nvidia-smi` is called to get the current watt reading (it's already awake, so this is safe).

## Tested hardware

| Machine | GPU | Kernel | Distro | Status |
|---|---|---|---|---|
| Lenovo Legion Pro 7 Gen 10 (16IAX10H) | RTX 5080 Mobile | 7.0.5-2-cachyos | CachyOS | ✅ Working |

Tested on your hardware? Open a PR to add it to the table.

## Troubleshooting

**Grey `?` icon:** PCI address not found. Run `lspci -d 10de:` to find your GPU address and pass it with `--pci-address`.

**Always green even when idle:** RTD3 is likely not enabled. Check `DynamicPowerManagement` in `/proc/driver/nvidia/params`.

**Service won't start:** Run `journalctl --user -u nvidia-state-tray` for details. Ensure PyQt6 is installed (`python -c "import PyQt6"`).
