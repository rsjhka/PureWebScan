#!/bin/bash
# PureWebScan - Linux/macOS Startup Script
# This script calls the cross-platform start.py

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    exit 1
fi

# Run the Python startup script
exec python3 "$SCRIPT_DIR/start.py" "$@"
