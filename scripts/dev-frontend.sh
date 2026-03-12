#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "node_modules not found. Running setup first..."
  bash "$SCRIPT_DIR/setup-frontend.sh"
fi

if [ ! -f ".env.local" ] && [ -f ".env.example" ]; then
  cp .env.example .env.local
fi

echo "Starting Next.js frontend on http://localhost:3000 ..."
npm run dev
