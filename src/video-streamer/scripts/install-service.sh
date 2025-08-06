#!/bin/bash

# Video Streamer Service Installation Script

set -e

SERVICE_NAME="video-streamer"
SERVICE_FILE="video-streamer.service"
SYSTEMD_DIR="/etc/systemd/system"
BINARY_NAME="video-streamer"

echo "🚀 Installing Video Streamer systemd service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Check if the binary exists
if [ ! -f "./$BINARY_NAME" ]; then
    echo "❌ Binary '$BINARY_NAME' not found. Please build it first with: go build -o $BINARY_NAME server.go"
    exit 1
fi

# Check if the service file exists
if [ ! -f "./scripts/$SERVICE_FILE" ]; then
    echo "❌ Service file '$SERVICE_FILE' not found."
    exit 1
fi

# Stop the service if it's running
echo "🛑 Stopping service if running..."
systemctl stop $SERVICE_NAME 2>/dev/null || true

# Copy service file to systemd directory
echo "📁 Copying service file to $SYSTEMD_DIR..."
cp scripts/$SERVICE_FILE $SYSTEMD_DIR/

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service
echo "✅ Enabling service..."
systemctl enable $SERVICE_NAME

echo ""
echo "🎉 Service installed successfully!"
echo ""
echo "📋 Available commands:"
echo "  Start service:    sudo systemctl start $SERVICE_NAME"
echo "  Stop service:     sudo systemctl stop $SERVICE_NAME"
echo "  Restart service:  sudo systemctl restart $SERVICE_NAME"
echo "  Check status:     sudo systemctl status $SERVICE_NAME"
echo "  View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo "  Disable service:  sudo systemctl disable $SERVICE_NAME"
echo ""
echo "🔧 To customize the service, edit: $SYSTEMD_DIR/$SERVICE_FILE"
echo "    Then run: sudo systemctl daemon-reload && sudo systemctl restart $SERVICE_NAME"
