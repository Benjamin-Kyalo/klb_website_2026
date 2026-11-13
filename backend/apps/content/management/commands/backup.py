"""Create a backup of the database and media files.

Usage:
    python manage.py backup                    # backup everything
    python manage.py backup --database-only     # database only
    python manage.py backup --media-only        # media files only
    python manage.py backup --output /path/to/dir  # custom output directory
"""
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a backup of the database and media files."

    def add_arguments(self, parser):
        parser.add_argument("--database-only", action="store_true", help="Backup only the database.")
        parser.add_argument("--media-only", action="store_true", help="Backup only media files.")
        parser.add_argument("--output", default=None, help="Output directory for the backup.")

    def handle(self, *args, **options):
        if options["database_only"] and options["media_only"]:
            raise CommandError("Choose either --database-only or --media-only, not both.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(options["output"] or settings.BACKUP_ROOT)
        output_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"klb_backup_{timestamp}"
        # Two backups can be requested within the same second; never overwrite
        # an existing archive.
        counter = 2
        while (output_dir / f"{backup_name}.zip").exists():
            backup_name = f"klb_backup_{timestamp}_{counter}"
            counter += 1
        backup_path = output_dir / f"{backup_name}.zip"
        # Build the archive under a temporary name first. A half-written .zip
        # must never be left behind for a later restore to trust.
        temp_path = output_dir / f".{backup_name}.part"

        self.stdout.write(f"Creating backup: {backup_path}")

        db_included = False

        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Database backup
                if not options["media_only"]:
                    self.stdout.write("  Backing up database...")
                    # Always dump JSON. It is database-engine independent and can
                    # be reloaded on any host with `manage.py loaddata`. Capture
                    # to a text buffer first so the file is written as UTF-8 on
                    # every platform (Windows default codec is not UTF-8).
                    db_file = output_dir / f"{backup_name}_db.json"
                    try:
                        from io import StringIO

                        buffer = StringIO()
                        call_command(
                            "dumpdata",
                            "--natural-foreign",
                            "--natural-primary",
                            stdout=buffer,
                            verbosity=0,
                        )
                        payload = buffer.getvalue()
                        if not payload.strip():
                            raise RuntimeError("dumpdata produced an empty file")
                        db_file.write_text(payload, encoding="utf-8")
                        if not db_file.exists() or db_file.stat().st_size == 0:
                            raise RuntimeError("dumpdata produced an empty file")
                        zf.write(db_file, f"{backup_name}/database.json")
                        db_included = True
                        self.stdout.write(self.style.SUCCESS("  Database backed up (JSON dump)."))
                    except Exception as e:
                        # A "database backup" without a database is useless.
                        raise CommandError(f"Could not dump the database: {e}") from e
                    finally:
                        if db_file.exists():
                            db_file.unlink()

                # Media files backup
                if not options["database_only"]:
                    self.stdout.write("  Backing up media files...")
                    media_root = Path(settings.MEDIA_ROOT)
                    if media_root.exists():
                        count = 0
                        for file_path in media_root.rglob("*"):
                            if file_path.is_file():
                                arcname = f"{backup_name}/media/{file_path.relative_to(media_root)}"
                                zf.write(file_path, arcname)
                                count += 1
                        self.stdout.write(self.style.SUCCESS(f"  Media backed up ({count} files)."))
                    else:
                        self.stdout.write(self.style.WARNING("  Media directory not found."))

                # Metadata. Never store credentials, only the database host.
                db_url = (os.getenv("DATABASE_URL") or "").strip()
                metadata = {
                    "created_at": datetime.now().isoformat(),
                    "database_url": db_url.split("@")[-1] if "@" in db_url else "local",
                    "backup_type": "full"
                    if not (options["database_only"] or options["media_only"])
                    else ("database" if options["database_only"] else "media"),
                    "database_included": db_included,
                }
                zf.writestr(f"{backup_name}/metadata.json", json.dumps(metadata, indent=2))
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        temp_path.replace(backup_path)

        self.stdout.write(self.style.SUCCESS(f"\nBackup complete: {backup_path}"))
        self.stdout.write(f"Size: {backup_path.stat().st_size / 1024:.1f} KB")
