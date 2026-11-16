#!/usr/bin/env bash
# Start the Django development server against a local database.
#
# The development settings refuse to start against Supabase, so export a local
# DATABASE_URL first:
#   DATABASE_URL="postgres://klb:klb_dev_password@127.0.0.1:5432/klb" ./scripts/dev-backend.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [ ! -d "$BACKEND/.venv" ]; then
  echo "The virtual environment is missing. Run ./scripts/setup-unix.sh first." >&2
  exit 1
fi

cd "$BACKEND"
source .venv/bin/activate
python manage.py runserver "${1:-127.0.0.1:8000}" --settings=config.dev_settings
