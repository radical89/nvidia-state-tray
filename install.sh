#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
SERVICE_DIR="$HOME/.config/systemd/user"

mkdir -p "$BIN_DIR" "$SERVICE_DIR"

install -m 755 "$SCRIPT_DIR/nvidia_state_tray.py" "$BIN_DIR/nvidia-state-tray"
install -m 644 "$SCRIPT_DIR/nvidia-state-tray.service" "$SERVICE_DIR/nvidia-state-tray.service"

systemctl --user daemon-reload
systemctl --user enable --now nvidia-state-tray.service

echo "Installed. The tray icon should appear within a few seconds."
echo "To check status: systemctl --user status nvidia-state-tray"
