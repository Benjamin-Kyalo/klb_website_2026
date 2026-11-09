#!/usr/bin/env bash
# Set up the KLB website on macOS or Linux.
# Usage:
#   ./scripts/setup-unix.sh
#   ./scripts/setup-unix.sh --skip-build

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
SKIP_BUILD=0

for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ is required." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js 20+ is required." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required." >&2; exit 1; }

echo "KLB website setup"
echo "Project: $ROOT"

cd "$BACKEND"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "Created backend/.env from .env.example."
  echo "Edit backend/.env and set DJANGO_SECRET_KEY, DATABASE_URL,"
  echo "SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD, then run this script again."
  exit 1
fi

cd "$FRONTEND"
npm install

# This script uses the PostgreSQL server already installed on this computer.
# Create the user and database first (see docs/SETUP.md step 3), then set
# DATABASE_URL in backend/.env.
echo "Waiting for the database..."
cd "$BACKEND"
python - <<'PY'
import os
import time

import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is not set in backend/.env")

last_error = None
for _ in range(15):
    try:
        with psycopg.connect(url, connect_timeout=3):
            print("Database is ready.")
            raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(2)

print("The database did not become ready.")
print(f"Last error: {last_error}")
print("Check that PostgreSQL is running and that DATABASE_URL in backend/.env is correct.")
print("Create the user and database first - see docs/SETUP.md step 3.")
raise SystemExit(1)
PY

python manage.py migrate
python manage.py seed_content

if [ "$SKIP_BUILD" -eq 0 ]; then
  cd "$FRONTEND"
  npm run build
  cd "$BACKEND"
  python manage.py collectstatic --noinput
fi

cd "$ROOT"
echo
echo "Setup finished."
echo "Backend:  ./scripts/dev-backend.sh"
echo "Frontend: ./scripts/dev-frontend.sh"
echo "Open http://localhost:5173 and sign in at /admin"
