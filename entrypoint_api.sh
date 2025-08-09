#!/bin/bash
set -euo pipefail

# Start desktop + noVNC from the demo image in background; do not block API
./start_all.sh &
./novnc_startup.sh &

# Start FastAPI
exec uvicorn app.main:app --host 0.0.0.0 --port 8000


