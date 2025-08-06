# Video Streamer Makefile

BINARY_NAME := nebula-video-streamer
SERVICE_NAME := nebula-video-streamer
GO_FILES := $(wildcard *.go) $(wildcard internal/**/*.go)

# Default target
.PHONY: all build clean run service-install service-start service-stop service-status service-logs service help
all: build

# Build the application
build: $(BINARY_NAME)

$(BINARY_NAME): $(GO_FILES)
	@echo "Building $(BINARY_NAME)..."
	go build -o $(BINARY_NAME) main.go

# Clean build artifacts
clean:
	@echo "Cleaning..."
	rm -f $(BINARY_NAME)
	go clean

# Run locally
run: build
	./$(BINARY_NAME)

# Install systemd service
service-install: build
	@if [ "$$(id -u)" -ne 0 ]; then echo "Run with sudo"; exit 1; fi
	systemctl stop nebula-video-streamer 2>/dev/null || true
	cp scripts/nebula-video-streamer.service /etc/systemd/system/
	systemctl daemon-reload
	systemctl enable nebula-video-streamer
	@echo "Service installed. Start with: sudo systemctl start nebula-video-streamer"

# Start service
service-start:
	@if [ "$$(id -u)" -ne 0 ]; then echo "Run with sudo"; exit 1; fi
	systemctl start nebula-video-streamer

# Stop service
service-stop:
	@if [ "$$(id -u)" -ne 0 ]; then echo "Run with sudo"; exit 1; fi
	systemctl stop nebula-video-streamer

# Check service status
service-status:
	systemctl status nebula-video-streamer

# View logs
service-logs:
	journalctl -u nebula-video-streamer -f

# Service (build + install + start)
service: build service-install start
	@echo "Deployed! Access at rtsp://localhost:8554/"

# Show help
help:
	@echo "Video Streamer Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make build    - Build the application"
	@echo "  make run      - Run locally"
	@echo "  make clean    - Clean build files"
	@echo ""
	@echo "Service (requires sudo):"
	@echo "  make service-install - Install systemd service"
	@echo "  make service-start    - Start service"
	@echo "  make service-stop     - Stop service"
	@echo "  make service-status   - Check service status"
	@echo "  make service-logs     - View service logs"
	@echo "  make service   - Full deployment"

.DEFAULT_GOAL := help
