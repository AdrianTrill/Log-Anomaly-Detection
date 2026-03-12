#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
  echo "Virtual environment not found. Running setup first..."
  bash "$SCRIPT_DIR/setup-backend.sh"
fi

source venv/bin/activate

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

echo "Starting FastAPI backend on http://localhost:8000 ..."
uvicorn app.main:app --reload --port 8000
