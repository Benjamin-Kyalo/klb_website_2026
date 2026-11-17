"""Tests for the seed_content release gate.

The production deploy runs ``seed_content --refresh`` on every build. These
tests prove that the command refreshes content once per seed release, keeps
later dashboard edits, and can still be forced back to the seed copy.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .management.commands.seed_content import seed_fingerprint
from .models import Page, Resource, SiteSetting


class SeedContentRevisionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())

    def _home_section(self):
        page = Page.objects.get(slug="home")
        return page.sections.first()

    def test_refresh_applies_seed_once_and_keeps_dashboard_edits(self):
        self.assertEqual(SiteSetting.load().seed_revision, "")
        home = Page.objects.get(slug="home")
        self.assertIn("data-count", home.sections.get(label="Hero").html)

        call_command("seed_content", "--refresh", stdout=StringIO())
        self.assertEqual(SiteSetting.load().seed_revision, seed_fingerprint())

        section = self._home_section()
        section.html = '<p id="dashboard-edit">Edited in the dashboard</p>'
        section.save()

        call_command("seed_content", "--refresh", stdout=StringIO())
        section.refresh_from_db()
        self.assertIn("dashboard-edit", section.html)

    def test_force_refresh_restores_the_seed_copy(self):
        call_command("seed_content", "--refresh", stdout=StringIO())
        section = self._home_section()
        section.html = '<p id="dashboard-edit">Edited in the dashboard</p>'
        section.save()

        call_command("seed_content", "--force-refresh", stdout=StringIO())
        seed_section = Page.objects.get(slug="home").sections.get(label="Hero")
        self.assertNotIn("dashboard-edit", seed_section.html)
        self.assertIn("data-count", seed_section.html)

    def test_plain_seed_never_overwrites_existing_rows(self):
        section = self._home_section()
        section.html = '<p id="dashboard-edit">Edited in the dashboard</p>'
        section.save()

        call_command("seed_content", stdout=StringIO())
        section.refresh_from_db()
        self.assertIn("dashboard-edit", section.html)

    def test_seed_repairs_backslash_document_links(self):
        resource = Resource.objects.first()
        resource.file_url = "assets\\docs\\KLB-PRICE-LIST-2026.pdf"
        resource.save(update_fields=["file_url"])

        call_command("seed_content", stdout=StringIO())
        resource.refresh_from_db()
        self.assertNotIn("\\", resource.file_url)
        self.assertTrue(resource.file_url.startswith("/assets/docs/"))
