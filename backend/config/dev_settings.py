"""Local development settings that never touch production.

Point DATABASE_URL at a local PostgreSQL database before using this module.
The guard below refuses to run against Supabase so a review session cannot
accidentally edit production content.

    $env:DATABASE_URL = "postgres://postgres:1234@127.0.0.1:5432/klb_verify"
    python manage.py migrate --settings=config.dev_settings
    python manage.py seed_content --settings=config.dev_settings
    python manage.py runserver --settings=config.dev_settings

Media and backups are written to backend/media and backend/backups, both of
which are already ignored by git.
"""
import os
from pathlib import Path

from .settings import *  # noqa: F401,F403

_DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if "supabase" in _DATABASE_URL.lower():
    raise RuntimeError(
        "config.dev_settings refuses to run against Supabase. Set DATABASE_URL "
        "to a local PostgreSQL database (for example "
        "postgres://postgres:1234@127.0.0.1:5432/klb_verify) before starting."
    )

BASE = Path(__file__).resolve().parent.parent

if not _DATABASE_URL:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE / "dev.sqlite3",
        }
    }

MEDIA_ROOT = BASE / "media"
BACKUP_ROOT = BASE / "backups"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

DEBUG = True
