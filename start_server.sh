#!/bin/bash
# PyFluff Server Startup Script
# 
# This script starts the PyFluff web server with proper environment setup.
# Usage: ./start_server.sh [options]
#
# Options:
#   --host HOST       Host to bind to (default: 0.0.0.0)
#   --port PORT       Port to bind to (default: 8080)
#   --reload          Enable auto-reload for development
#   --help            Show this help message

set -e

# Default configuration
HOST="${PYFLUFF_HOST:-0.0.0.0}"
PORT="${PYFLUFF_PORT:-8080}"
RELOAD_FLAG=""
LOG_LEVEL="${PYFLUFF_LOG_LEVEL:-info}"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --reload)
            RELOAD_FLAG="--reload"
            shift
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help)
            echo "PyFluff Server Startup Script"
            echo ""
            echo "Usage: ./start_server.sh [options]"
            echo ""
            echo "Options:"
            echo "  --host HOST       Host to bind to (default: 0.0.0.0)"
            echo "  --port PORT       Port to bind to (default: 8080)"
            echo "  --reload          Enable auto-reload for development"
            echo "  --log-level LEVEL Log level (default: info)"
            echo "  --help            Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  PYFLUFF_HOST      Override default host"
            echo "  PYFLUFF_PORT      Override default port"
            echo "  PYFLUFF_LOG_LEVEL Override default log level"
            echo ""
            echo "Examples:"
            echo "  ./start_server.sh"
            echo "  ./start_server.sh --port 3000"
            echo "  ./start_server.sh --reload"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run './start_server.sh --help' for usage information"
            exit 1
            ;;
    esac
done

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================"
echo "PyFluff Server Startup"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    echo "Please install Python 3.11 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "Error: Python 3.11 or later is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"

# Check for virtual environment
echo ""
echo "Checking virtual environment..."
if [ ! -d "venv" ]; then
    echo "Warning: Virtual environment not found"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
if ! python3 -c "import pyfluff" 2>/dev/null; then
    echo "Warning: PyFluff package not found"
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e .
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies OK"
fi

# Check Bluetooth (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "Checking Bluetooth..."
    if command -v bluetoothctl &> /dev/null; then
        if systemctl is-active --quiet bluetooth; then
            echo "✓ Bluetooth service running"
        else
            echo "Warning: Bluetooth service not running"
            echo "Starting Bluetooth service..."
            sudo systemctl start bluetooth || echo "Could not start Bluetooth (may require sudo)"
        fi
    else
        echo "Warning: bluetoothctl not found (Bluetooth may not be available)"
    fi
fi

# Display server information
echo ""
echo "======================================"
echo "Starting PyFluff Server"
echo "======================================"
echo ""
echo "Server Configuration:"
echo "  Host:      $HOST"
echo "  Port:      $PORT"
echo "  Log Level: $LOG_LEVEL"
if [ -n "$RELOAD_FLAG" ]; then
    echo "  Mode:      Development (auto-reload enabled)"
else
    echo "  Mode:      Production"
fi
echo ""
echo "Access the web interface at:"
if [ "$HOST" = "0.0.0.0" ]; then
    echo "  Local:  http://localhost:$PORT"
    # Cross-platform: get primary network IP address
    get_ip_address() {
        # Try Linux (hostname -I)
        if command -v hostname >/dev/null 2>&1; then
            ip=$(hostname -I 2>/dev/null | awk '{print $1}')
            if [ -n "$ip" ]; then
                echo "$ip"
                return
            fi
        fi
        # Try macOS (ipconfig getifaddr en0)
        if command -v ipconfig >/dev/null 2>&1; then
            ip=$(ipconfig getifaddr en0 2>/dev/null)
            if [ -n "$ip" ]; then
                echo "$ip"
                return
            fi
            # Try en1 (Ethernet) if en0 fails
            ip=$(ipconfig getifaddr en1 2>/dev/null)
            if [ -n "$ip" ]; then
                echo "$ip"
                return
            fi
        fi
        # Try ifconfig (BSD fallback)
        if command -v ifconfig >/dev/null 2>&1; then
            ip=$(ifconfig 2>/dev/null | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}')
            if [ -n "$ip" ]; then
                echo "$ip"
                return
            fi
        fi
        # Fallback
        echo "<your-ip>"
    }
    echo "  Network: http://$(get_ip_address):$PORT"
else
    echo "  http://$HOST:$PORT"
fi
echo ""
echo "API documentation available at:"
if [ "$HOST" = "0.0.0.0" ]; then
    echo "  http://localhost:$PORT/docs"
else
    echo "  http://$HOST:$PORT/docs"
fi
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"
echo ""

# Start the server
exec uvicorn pyfluff.server:app --host "$HOST" --port "$PORT" --log-level "$LOG_LEVEL" $RELOAD_FLAG
