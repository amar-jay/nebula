#!/bin/bash

# Video Streamer Service Uninstallation Script

set -e

SERVICE_NAME="nebula-video-streamer"
SERVICE_FILE="nebula-video-streamer.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "🗑️  Uninstalling Video Streamer systemd service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Stop the service if it's running
echo "🛑 Stopping service..."
systemctl stop $SERVICE_NAME 2>/dev/null || true

# Disable the service
echo "❌ Disabling service..."
systemctl disable $SERVICE_NAME 2>/dev/null || true

# Remove service file
if [ -f "$SYSTEMD_DIR/$SERVICE_FILE" ]; then
    echo "🗑️  Removing service file..."
    rm "$SYSTEMD_DIR/$SERVICE_FILE"
else
    echo "⚠️  Service file not found at $SYSTEMD_DIR/$SERVICE_FILE"
fi

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "✅ Service uninstalled successfully!"
echo "   The binary and source code remain in the current directory."
