#!/bin/bash

# Beat Visualizer - Start Script
# This script starts both the backend and frontend servers

echo "🎵 Starting Beat Visualizer..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Kill any existing processes on our ports
cleanup_existing() {
    local port=$1
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo -e "${BLUE}Killing existing process on port $port (PID: $pid)${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# Clean up any lingering processes from previous runs
cleanup_existing 8000
cleanup_existing 5173

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: FFmpeg is not installed${NC}"
    echo "Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
    exit 1
fi

# Setup Python virtual environment if needed
if [ ! -d "$SCRIPT_DIR/backend/.venv" ]; then
    echo -e "${BLUE}Setting up Python virtual environment...${NC}"
    cd "$SCRIPT_DIR/backend"
    python3 -m venv .venv
    cd "$SCRIPT_DIR"
fi

# Activate venv and install/update dependencies
source "$SCRIPT_DIR/backend/.venv/bin/activate"
echo -e "${BLUE}Checking Python dependencies...${NC}"
pip install -q -r "$SCRIPT_DIR/backend/requirements.txt"

# Setup frontend dependencies
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    npm install
else
    echo -e "${BLUE}Checking frontend dependencies...${NC}"
    npm install --silent
fi
cd "$SCRIPT_DIR"

# Track PIDs
BACKEND_PID=""
FRONTEND_PID=""

# Cleanup function - kills processes and their children
cleanup() {
    echo ""
    echo "Shutting down..."
    
    # Kill backend and all its children
    if [ -n "$BACKEND_PID" ]; then
        pkill -P $BACKEND_PID 2>/dev/null
        kill $BACKEND_PID 2>/dev/null
    fi
    
    # Kill frontend and all its children
    if [ -n "$FRONTEND_PID" ]; then
        pkill -P $FRONTEND_PID 2>/dev/null
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    # Force kill anything still on our ports
    cleanup_existing 8000
    cleanup_existing 5173
    
    echo "Done."
    exit 0
}

# Trap multiple signals including EXIT for when terminal closes
trap cleanup SIGINT SIGTERM EXIT SIGHUP

# Start backend
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
cd "$SCRIPT_DIR/backend"
source .venv/bin/activate
python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start${NC}"
    exit 1
fi

# Start frontend
echo -e "${GREEN}Starting frontend on http://localhost:5173${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✓ Beat Visualizer is running!${NC}"
echo ""
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID

