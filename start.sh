#!/bin/bash
set -e

# Start sneaks-service in background on port 3001 (NOT the Cloud Run PORT)
echo "Starting sneaks-service on port 3001..."
cd /app/sneaks-service
PORT=3001 node server.js &
SNEAKS_PID=$!

# Wait for sneaks-service to be ready
for i in $(seq 1 10); do
    if curl -s http://localhost:3001/health > /dev/null 2>&1; then
        echo "sneaks-service ready"
        break
    fi
    sleep 1
done

# Start FastAPI backend on Cloud Run's PORT (default 8000)
BACKEND_PORT="${PORT:-8000}"
echo "Starting FastAPI backend on port ${BACKEND_PORT}..."
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" --workers 1
