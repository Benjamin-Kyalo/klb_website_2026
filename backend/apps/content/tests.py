"""Tests for the backup, settings and theme admin APIs.

Run with:
    python manage.py test apps.content --settings=config.test_settings
"""
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import ActivityLog, User

from .models import BackupRecord, SiteSetting, WebsiteTheme


def build_archive(*, include_db=True, include_media=False, invalid_db=False, traversal=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        if include_db:
            payload = "this is not json" if invalid_db else json.dumps([])
            zf.writestr("klb_backup_test/database.json", payload)
        if include_media:
            zf.writestr("klb_backup_test/media/uploads/hello.txt", "hello")
        if traversal:
            zf.writestr("klb_backup_test/media/../../../evil.txt", "evil")
        zf.writestr(
            "klb_backup_test/metadata.json",
            json.dumps({"backup_type": "full"}),
        )
    return buffer.getvalue()


class AdminTestCase(TestCase):
    def setUp(self):
        # Files are not rolled back with the database, so start each test with
        # empty media and backup folders.
        for path in Path(settings.BACKUP_ROOT).glob("*"):
            if path.is_file():
                path.unlink()
        for path in Path(settings.MEDIA_ROOT).rglob("*"):
            if path.is_file():
                path.unlink()
        self.admin = User.objects.create_user(
            username="super",
            email="super@example.com",
            password="StrongPass!2026",
            role=User.Role.SUPER_ADMIN,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)


class BackupApiTests(AdminTestCase):
    def _create(self, components):
        return self.client.post(
            reverse("admin-backup"),
            {"components": components},
            format="json",
        )

    def test_full_backup_contains_database_and_media(self):
        media_dir = Path(settings.MEDIA_ROOT) / "uploads"
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "sample.txt").write_text("sample", encoding="utf-8")

        response = self._create(["database", "media"])

        self.assertEqual(response.status_code, 200, response.data)
        record = BackupRecord.objects.get(pk=response.data["id"])
        self.assertEqual(record.backup_type, BackupRecord.BackupType.FULL)
        archive = Path(settings.BACKUP_ROOT) / record.filename
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
        self.assertTrue(any(name.endswith("database.json") for name in names))
        self.assertTrue(any("/media/uploads/sample.txt" in name for name in names))
        self.assertTrue(
            ActivityLog.objects.filter(action=ActivityLog.Action.BACKUP).exists()
        )

    def test_database_only_backup(self):
        response = self._create(["database"])
        self.assertEqual(response.status_code, 200, response.data)
        record = BackupRecord.objects.get(pk=response.data["id"])
        self.assertEqual(record.backup_type, BackupRecord.BackupType.DATABASE)
        with zipfile.ZipFile(Path(settings.BACKUP_ROOT) / record.filename) as zf:
            names = zf.namelist()
        self.assertTrue(any(name.endswith("database.json") for name in names))
        self.assertFalse(any("/media/" in name for name in names))

    def test_media_only_backup(self):
        response = self._create(["media"])
        self.assertEqual(response.status_code, 200, response.data)
        record = BackupRecord.objects.get(pk=response.data["id"])
        self.assertEqual(record.backup_type, BackupRecord.BackupType.MEDIA)
        with zipfile.ZipFile(Path(settings.BACKUP_ROOT) / record.filename) as zf:
            names = zf.namelist()
        self.assertFalse(any(name.endswith("database.json") for name in names))

    def test_cannot_create_without_components(self):
        response = self._create([])
        self.assertEqual(response.status_code, 400)
        self.assertIn("component", response.data["detail"].lower())

    def test_failed_attempt_is_recorded(self):
        with patch(
            "apps.content.views.call_command", side_effect=RuntimeError("dump exploded")
        ):
            response = self._create(["database"])
        self.assertEqual(response.status_code, 500)
        record = BackupRecord.objects.get(pk=response.data["id"])
        self.assertEqual(record.status, BackupRecord.Status.FAILED)
        self.assertIn("dump exploded", record.error)

    def test_download_returns_the_archive(self):
        create = self._create(["database"])
        record = BackupRecord.objects.get(pk=create.data["id"])
        response = self.client.get(reverse("admin-backup-download", args=[record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        payload = b"".join(response.streaming_content)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(payload)))

    def test_upload_accepts_a_valid_archive(self):
        upload = SimpleUploadedFile(
            "imported.zip", build_archive(include_db=True, include_media=True)
        )
        response = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        record = BackupRecord.objects.get(pk=response.data["id"])
        self.assertEqual(record.components, ["database", "media"])
        self.assertTrue((Path(settings.BACKUP_ROOT) / record.filename).is_file())

    def test_upload_rejects_invalid_zip(self):
        upload = SimpleUploadedFile("bad.zip", b"not a zip")
        response = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BackupRecord.objects.exists())

    def test_upload_rejects_zip_without_klb_content(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("photos/cat.jpg", "meow")
        upload = SimpleUploadedFile("other.zip", buffer.getvalue())
        response = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_sanitises_the_filename(self):
        upload = SimpleUploadedFile(
            "../../escape.zip", build_archive(include_db=True)
        )
        response = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        record = BackupRecord.objects.get(pk=response.data["id"])
        self.assertNotIn("..", record.filename)
        self.assertNotIn("/", record.filename)
        self.assertTrue((Path(settings.BACKUP_ROOT) / record.filename).is_file())

    def test_restore_media_creates_safety_backup_and_restores_files(self):
        upload = SimpleUploadedFile(
            "media-only.zip", build_archive(include_db=False, include_media=True)
        )
        created = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        record = BackupRecord.objects.get(pk=created.data["id"])
        target = Path(settings.MEDIA_ROOT) / "uploads" / "hello.txt"
        target.unlink(missing_ok=True)

        response = self.client.post(reverse("admin-backup-restore", args=[record.pk]))

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_text(encoding="utf-8"), "hello")
        record.refresh_from_db()
        self.assertIsNotNone(record.restored_at)
        # The safety backup is created before the restore happens.
        self.assertTrue(
            BackupRecord.objects.filter(
                backup_type=BackupRecord.BackupType.FULL
            ).exists()
        )

    def test_restore_rejects_invalid_database_json(self):
        upload = SimpleUploadedFile(
            "broken-db.zip", build_archive(include_db=True, invalid_db=True)
        )
        created = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        record = BackupRecord.objects.get(pk=created.data["id"])
        before = BackupRecord.objects.count()

        response = self.client.post(reverse("admin-backup-restore", args=[record.pk]))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(BackupRecord.objects.count(), before)

    def test_restore_does_not_write_outside_media_root(self):
        upload = SimpleUploadedFile(
            "traversal.zip",
            build_archive(include_db=False, include_media=True, traversal=True),
        )
        created = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        record = BackupRecord.objects.get(pk=created.data["id"])
        outside = Path(settings.MEDIA_ROOT).parent / "evil.txt"
        outside.unlink(missing_ok=True)

        response = self.client.post(reverse("admin-backup-restore", args=[record.pk]))

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(outside.exists())

    def test_restore_cancels_when_safety_backup_fails(self):
        upload = SimpleUploadedFile(
            "media-only.zip", build_archive(include_db=False, include_media=True)
        )
        created = self.client.post(
            reverse("admin-backup-upload"), {"file": upload}, format="multipart"
        )
        record = BackupRecord.objects.get(pk=created.data["id"])
        target = Path(settings.MEDIA_ROOT) / "uploads" / "hello.txt"
        target.unlink(missing_ok=True)

        with patch(
            "apps.content.views.call_command", side_effect=RuntimeError("no space")
        ):
            response = self.client.post(
                reverse("admin-backup-restore", args=[record.pk])
            )

        self.assertEqual(response.status_code, 500)
        self.assertFalse(target.exists())

    def test_delete_removes_record_and_file(self):
        created = self._create(["database"])
        record = BackupRecord.objects.get(pk=created.data["id"])
        archive = Path(settings.BACKUP_ROOT) / record.filename
        self.assertTrue(archive.is_file())

        response = self.client.delete(reverse("admin-backup-delete", args=[record.pk]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(archive.exists())
        self.assertFalse(BackupRecord.objects.filter(pk=record.pk).exists())

    def test_disk_sync_does_not_duplicate_rows(self):
        archive = Path(settings.BACKUP_ROOT) / "disk-only.zip"
        archive.write_bytes(build_archive(include_db=True))

        first = self.client.get(reverse("admin-backup"))
        second = self.client.get(reverse("admin-backup"))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            BackupRecord.objects.filter(filename="disk-only.zip").count(), 1
        )

    def test_duplicate_filename_is_rejected(self):
        BackupRecord.objects.create(
            filename="duplicate.zip", backup_type=BackupRecord.BackupType.DATABASE
        )
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            BackupRecord.objects.create(
                filename="duplicate.zip",
                backup_type=BackupRecord.BackupType.DATABASE,
            )

    def test_retention_keeps_only_configured_number(self):
        settings_obj = SiteSetting.load()
        settings_obj.backup_retention = 2
        settings_obj.save()

        for _ in range(4):
            response = self._create(["database"])
            self.assertEqual(response.status_code, 200, response.data)

        successes = BackupRecord.objects.filter(status=BackupRecord.Status.SUCCESS)
        self.assertEqual(successes.count(), 2)
        self.assertEqual(
            len(list(Path(settings.BACKUP_ROOT).glob("*.zip"))), 2
        )


class BackupPermissionTests(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.limited = User.objects.create_user(
            username="limited",
            email="limited@example.com",
            password="StrongPass!2026",
            role=User.Role.ADMINISTRATOR,
        )
        self.limited.permissions = {
            "backup": ["view", "create"],
        }
        self.limited.save()
        self.limited_client = APIClient()
        self.limited_client.force_authenticate(user=self.limited)
        self.record = BackupRecord.objects.create(
            filename="example.zip",
            backup_type=BackupRecord.BackupType.DATABASE,
            components=["database"],
            status=BackupRecord.Status.SUCCESS,
        )
        (Path(settings.BACKUP_ROOT) / "example.zip").write_bytes(
            build_archive(include_db=True)
        )

    def test_can_list_and_create(self):
        self.assertEqual(
            self.limited_client.get(reverse("admin-backup")).status_code, 200
        )
        self.assertEqual(
            self.limited_client.post(
                reverse("admin-backup"), {"components": ["database"]}, format="json"
            ).status_code,
            200,
        )

    def test_cannot_delete_without_delete_permission(self):
        response = self.limited_client.delete(
            reverse("admin-backup-delete", args=[self.record.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(BackupRecord.objects.filter(pk=self.record.pk).exists())

    def test_cannot_restore_without_delete_permission(self):
        response = self.limited_client.post(
            reverse("admin-backup-restore", args=[self.record.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_cannot_view_backups(self):
        editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
        )
        client = APIClient()
        client.force_authenticate(user=editor)
        self.assertEqual(client.get(reverse("admin-backup")).status_code, 403)


class SiteSettingApiTests(AdminTestCase):
    def test_admin_can_update_maintenance_and_retention(self):
        response = self.client.patch(
            reverse("admin-settings"),
            {
                "maintenance_mode": True,
                "maintenance_message": "We are updating the catalogue.",
                "backup_retention": 5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        settings_obj = SiteSetting.load()
        self.assertTrue(settings_obj.maintenance_mode)
        self.assertEqual(settings_obj.backup_retention, 5)
        self.assertTrue(
            ActivityLog.objects.filter(action=ActivityLog.Action.SETTINGS).exists()
        )

    def test_negative_retention_is_rejected(self):
        response = self.client.patch(
            reverse("admin-settings"),
            {"backup_retention": -1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_navigation_requires_super_admin(self):
        admin = User.objects.create_user(
            username="admin2",
            email="admin2@example.com",
            password="StrongPass!2026",
            role=User.Role.ADMINISTRATOR,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            reverse("admin-settings"),
            {"navigation": []},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_cannot_change_settings(self):
        editor = User.objects.create_user(
            username="editor",
            email="editor@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
        )
        client = APIClient()
        client.force_authenticate(user=editor)
        self.assertEqual(client.get(reverse("admin-settings")).status_code, 403)
        self.assertEqual(
            client.patch(
                reverse("admin-settings"), {"maintenance_mode": True}, format="json"
            ).status_code,
            403,
        )


class WebsiteThemeApiTests(AdminTestCase):
    def test_blank_slug_is_generated_from_name(self):
        response = self.client.post(
            reverse("admin-themes"),
            {"name": "Back to School 2026", "slug": "", "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["slug"], "back-to-school-2026")

    def test_name_is_required(self):
        response = self.client.post(
            reverse("admin-themes"), {"name": "", "slug": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_slug_is_reported_clearly(self):
        WebsiteTheme.objects.create(name="Existing", slug="existing")
        response = self.client.post(
            reverse("admin-themes"),
            {"name": "Another", "slug": "existing"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("slug", response.data["errors"])

    def test_theme_can_be_deactivated(self):
        theme = WebsiteTheme.objects.create(name="Campaign", slug="campaign")
        response = self.client.patch(
            reverse("admin-theme", args=[theme.pk]),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        theme.refresh_from_db()
        self.assertFalse(theme.is_active)
        self.assertEqual(theme.status, "inactive")
