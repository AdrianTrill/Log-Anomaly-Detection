#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Starting Log Anomaly Detection Platform ==="
echo ""

# Start backend in background
echo "[backend] Starting FastAPI on http://localhost:8000 ..."
bash "$SCRIPT_DIR/dev-backend.sh" &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend in foreground
echo "[frontend] Starting Next.js on http://localhost:3000 ..."
bash "$SCRIPT_DIR/dev-frontend.sh" &
FRONTEND_PID=$!

# Trap Ctrl+C to kill both
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

echo ""
echo "Both servers are running. Press Ctrl+C to stop."
echo "  Backend:  http://localhost:8000  (docs: http://localhost:8000/docs)"
echo "  Frontend: http://localhost:3000"
echo ""

wait
