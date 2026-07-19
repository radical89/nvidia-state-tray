#!/usr/bin/env bash
set -euo pipefail

systemctl --user disable --now nvidia-state-tray.service 2>/dev/null || true
rm -f "$HOME/.local/bin/nvidia-state-tray"
rm -f "$HOME/.config/systemd/user/nvidia-state-tray.service"
systemctl --user daemon-reload

echo "Uninstalled."
