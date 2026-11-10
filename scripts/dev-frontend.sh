#!/usr/bin/env bash
# Start the Vite development server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Frontend dependencies are missing. Run ./scripts/setup-unix.sh first." >&2
  exit 1
fi

cd "$FRONTEND"
npm run dev
