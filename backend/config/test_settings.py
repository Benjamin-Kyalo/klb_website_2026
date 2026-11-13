"""Isolated settings for automated tests.

Tests must never touch the Supabase database, the real media folder or the
production backup folder. This module swaps in an in-memory SQLite database
and temporary directories for both.

Run with:
    python manage.py test --settings=config.test_settings
"""
import tempfile
from pathlib import Path

from .settings import *  # noqa: F401,F403

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="klb-tests-"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MEDIA_ROOT = _TEST_ROOT / "media"
BACKUP_ROOT = _TEST_ROOT / "backups"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Keep files small during tests but large enough for real fixtures.
BACKUP_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
BACKUP_MAX_RESTORE_BYTES = 50 * 1024 * 1024
