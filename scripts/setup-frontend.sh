#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

cd "$FRONTEND_DIR"

echo "Installing dependencies..."
npm install

if [ ! -f ".env.local" ] && [ -f ".env.example" ]; then
  cp .env.example .env.local
  echo "Created .env.local from .env.example"
fi

echo ""
echo "Frontend setup complete."
echo "Run:  cd frontend && npm run dev"
