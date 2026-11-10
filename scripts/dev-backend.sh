#!/usr/bin/env bash
# Start the Django development server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [ ! -d "$BACKEND/.venv" ]; then
  echo "The virtual environment is missing. Run ./scripts/setup-unix.sh first." >&2
  exit 1
fi

cd "$BACKEND"
source .venv/bin/activate
python manage.py runserver "${1:-127.0.0.1:8000}"
