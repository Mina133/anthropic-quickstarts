#!/bin/bash
set -euo pipefail

# Ensure DISPLAY is exported for child processes
export DISPLAY=:${DISPLAY_NUM:-1}

# Start desktop + noVNC from the demo image (monitored internally)
./start_all.sh
./novnc_startup.sh

# Start FastAPI
exec uvicorn app.main:app --host 0.0.0.0 --port 8000


