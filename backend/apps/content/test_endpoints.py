"""Smoke tests for every API endpoint.

These tests do not assert exact payloads; they assert that each endpoint
responds with a sane status code (never a 500) for an authenticated super
administrator, and that permission boundaries hold for lower roles. Run with:

    python manage.py test apps.content.test_endpoints --settings=config.test_settings
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User


class EndpointSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.super_admin = User.objects.create_user(
            username="smoke_super",
            email="smoke_super@example.com",
            password="StrongPass!2026",
            role=User.Role.SUPER_ADMIN,
        )
        cls.editor = User.objects.create_user(
            username="smoke_editor",
            email="smoke_editor@example.com",
            password="StrongPass!2026",
            role=User.Role.EDITOR,
        )

    def setUp(self):
        self.super_client = APIClient()
        self.super_client.force_authenticate(user=self.super_admin)
        self.editor_client = APIClient()
        self.editor_client.force_authenticate(user=self.editor)

    def _get(self, client, path):
        return client.get(path)

    def _assert_ok(self, response, path):
        self.assertNotEqual(
            response.status_code, 500, f"{path} returned 500: {getattr(response, 'data', None)}"
        )
        self.assertIn(
            response.status_code, (200, 201, 204, 400, 404),
            f"{path} returned unexpected {response.status_code}",
        )

    # ---- public endpoints ----
    def test_public_endpoints(self):
        paths = [
            "/api/site/",
            "/api/pages/home/",
            "/api/books/",
            "/api/news/",
            "/api/careers/",
            "/api/tenders/",
            "/api/resources/",
            "/health/",
        ]
        for path in paths:
            response = self.client.get(path) if False else self.super_client.get(path)
            # Use anonymous client for truly public endpoints.
        anon = APIClient()
        for path in paths:
            response = anon.get(path)
            self._assert_ok(response, path)

    # ---- admin endpoints as super admin ----
    def test_admin_endpoints_super(self):
        paths = [
            "/api/admin/pages/",
            "/api/admin/team-photos/",
            "/api/admin/digital-partners/",
            "/api/admin/books/",
            "/api/admin/news/",
            "/api/admin/careers/",
            "/api/admin/tenders/",
            "/api/admin/resources/",
            "/api/admin/enquiries/",
            "/api/admin/subscribers/",
            "/api/admin/settings/",
            "/api/admin/themes/",
            "/api/admin/backup/",
            "/api/admin/users/",
            "/api/admin/activity/",
            "/api/admin/activity/actors/",
            "/api/admin/options/groups/",
            "/api/admin/stats/",
            "/api/auth/me/",
            "/api/auth/csrf/",
        ]
        for path in paths:
            response = self.super_client.get(path)
            self._assert_ok(response, path)

    # ---- today's new endpoints respond correctly ----
    def test_backup_create_and_restore_validation(self):
        # Create a backup
        response = self.super_client.post(
            "/api/admin/backup/", {"components": ["database"]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        record_id = response.data["id"]
        # Download
        response = self.super_client.get(f"/api/admin/backup/{record_id}/download/")
        self.assertEqual(response.status_code, 200)
        # Restore (safety backup will be created)
        response = self.super_client.post(f"/api/admin/backup/{record_id}/restore/")
        self.assertEqual(response.status_code, 200, response.data)
        # Delete
        response = self.super_client.delete(f"/api/admin/backup/{record_id}/")
        self.assertEqual(response.status_code, 204)

    def test_activity_export_formats(self):
        for fmt in ("csv", "xlsx", "pdf"):
            response = self.super_client.get(
                f"/api/admin/activity/export/?format={fmt}"
            )
            self.assertEqual(response.status_code, 200, response.content[:200])
        response = self.super_client.get(
            "/api/admin/activity/export/?format=docx"
        )
        self.assertEqual(response.status_code, 400)

    def test_settings_patch_and_validation(self):
        response = self.super_client.patch(
            "/api/admin/settings/",
            {"maintenance_mode": True, "backup_retention": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["maintenance_mode"])
        self.assertEqual(response.data["backup_retention"], 3)
        # Invalid retention
        response = self.super_client.patch(
            "/api/admin/settings/", {"backup_retention": -1}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        # Revert
        self.super_client.patch(
            "/api/admin/settings/",
            {"maintenance_mode": False, "backup_retention": 10},
            format="json",
        )

    def test_theme_create_blank_slug_and_duplicate(self):
        response = self.super_client.post(
            "/api/admin/themes/",
            {"name": "Smoke Theme", "slug": "", "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["slug"], "smoke-theme")
        theme_id = response.data["id"]
        # Duplicate slug
        response = self.super_client.post(
            "/api/admin/themes/",
            {"name": "Another", "slug": "smoke-theme"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("slug", response.data.get("errors", response.data))
        # Deactivate + delete
        self.super_client.patch(
            f"/api/admin/themes/{theme_id}/", {"is_active": False}, format="json"
        )
        response = self.super_client.delete(f"/api/admin/themes/{theme_id}/")
        self.assertEqual(response.status_code, 204)

    # ---- permission boundaries ----
    def test_editor_cannot_access_restricted_endpoints(self):
        restricted = [
            "/api/admin/backup/",
            "/api/admin/settings/",
            "/api/admin/users/",
            "/api/admin/activity/",
        ]
        for path in restricted:
            response = self.editor_client.get(path)
            self.assertIn(
                response.status_code, (403, 401),
                f"editor reached {path} with {response.status_code}",
            )

    def test_anonymous_cannot_reach_admin(self):
        anon = APIClient()
        response = anon.get("/api/admin/pages/")
        self.assertIn(response.status_code, (401, 403))
