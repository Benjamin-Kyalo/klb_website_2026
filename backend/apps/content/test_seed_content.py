"""Tests for the non-destructive seed_content command.

The production deploy runs ``seed_content --refresh`` on every build. These
tests prove that the deploy path keeps content created or edited in the
dashboard, that restore modes keep dashboard-created rows/sections/settings,
that restore modes are explicit, and that a safety dump is written before any
seed row is rewritten.
"""
import json
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.catalogue.models import Book

from .management.commands.seed_content import seed_fingerprint
from .models import (
    Career,
    DigitalPartner,
    News,
    Page,
    Resource,
    Section,
    SiteSetting,
    Tender,
)


class SeedContentRevisionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", stdout=StringIO())

    def setUp(self):
        # Keep safety dumps out of the repository and isolated per test.
        self._backup_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._backup_temp.cleanup)
        override = override_settings(BACKUP_ROOT=Path(self._backup_temp.name))
        override.enable()
        self.addCleanup(override.disable)

    # -- helpers -------------------------------------------------------
    def _home_section(self):
        page = Page.objects.get(slug="home")
        return page.sections.get(label="Hero")

    def _add_dashboard_content(self):
        """Create the kind of content an editor adds in the dashboard."""
        page = Page.objects.create(slug="dashboard-page", title="Dashboard page")
        dashboard_section = Section.objects.create(
            page=Page.objects.get(slug="home"),
            label="Dashboard notice",
            kind=Section.Kind.HTML,
            html='<p id="dashboard-notice">Added in the dashboard</p>',
            sort_order=99,
        )
        page_section = Section.objects.create(
            page=page,
            label="Dashboard page section",
            kind=Section.Kind.HTML,
            html='<p id="dashboard-page-copy">Dashboard page copy</p>',
        )
        News.objects.create(
            title="Dashboard news",
            slug="dashboard-news",
            published_at=date(2026, 11, 17),
            summary="Added in the dashboard",
        )
        Career.objects.create(title="Dashboard vacancy", location="Nairobi")
        Tender.objects.create(title="Dashboard tender", category="Goods")
        Resource.objects.create(
            title="Dashboard resource",
            category="Forms",
            file_url="/assets/docs/dashboard.pdf",
        )
        DigitalPartner.objects.create(key="dashboard-partner", name="Dashboard partner")
        Book.objects.create(slug="dashboard-book", title="Dashboard book")
        return page, dashboard_section, page_section

    def _assert_dashboard_content_exists(self):
        self.assertTrue(Page.objects.filter(slug="dashboard-page").exists())
        self.assertTrue(
            Section.objects.filter(
                page__slug="home", label="Dashboard notice", html__contains="dashboard-notice"
            ).exists()
        )
        self.assertTrue(
            Section.objects.filter(
                page__slug="dashboard-page", html__contains="dashboard-page-copy"
            ).exists()
        )
        self.assertTrue(News.objects.filter(slug="dashboard-news").exists())
        self.assertTrue(Career.objects.filter(title="Dashboard vacancy").exists())
        self.assertTrue(Tender.objects.filter(title="Dashboard tender").exists())
        self.assertTrue(Resource.objects.filter(title="Dashboard resource").exists())
        self.assertTrue(DigitalPartner.objects.filter(key="dashboard-partner").exists())
        self.assertTrue(Book.objects.filter(slug="dashboard-book").exists())

    # -- deploy path ---------------------------------------------------
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

    def test_new_seed_revision_is_create_only(self):
        """A deploy that sees a new seed file must not rewrite existing rows."""
        SiteSetting.objects.filter(pk=1).update(seed_revision="previous-release")
        section = self._home_section()
        section.html = '<p id="dashboard-edit">Edited in the dashboard</p>'
        section.save()
        home = Page.objects.get(slug="home")
        home.title = "Dashboard home title"
        home.save(update_fields=["title"])
        article = News.objects.order_by("id").first()
        article.summary = "Dashboard news summary"
        article.save(update_fields=["summary"])
        settings_obj = SiteSetting.load()
        settings_obj.site_name = "Dashboard Site Name"
        settings_obj.statistics = [{"value": "9", "label": "Dashboard statistic"}]
        settings_obj.save(update_fields=["site_name", "statistics"])

        call_command("seed_content", "--refresh", stdout=StringIO())

        section.refresh_from_db()
        self.assertIn("dashboard-edit", section.html)
        home.refresh_from_db()
        self.assertEqual(home.title, "Dashboard home title")
        article.refresh_from_db()
        self.assertEqual(article.summary, "Dashboard news summary")
        settings_obj.refresh_from_db()
        self.assertEqual(settings_obj.site_name, "Dashboard Site Name")
        self.assertEqual(settings_obj.statistics, [{"value": "9", "label": "Dashboard statistic"}])
        self.assertEqual(settings_obj.seed_revision, seed_fingerprint())

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

    # -- forced restore -------------------------------------------------
    def test_force_refresh_restores_the_seed_copy_of_seed_rows(self):
        call_command("seed_content", "--refresh", stdout=StringIO())
        section = self._home_section()
        section.html = '<p id="dashboard-edit">Edited in the dashboard</p>'
        section.save()

        call_command("seed_content", "--force-refresh", stdout=StringIO())
        seed_section = Page.objects.get(slug="home").sections.get(label="Hero")
        self.assertNotIn("dashboard-edit", seed_section.html)
        self.assertIn("data-count", seed_section.html)

    def test_force_refresh_keeps_dashboard_created_rows_and_sections(self):
        self._add_dashboard_content()

        call_command("seed_content", "--force-refresh", stdout=StringIO())

        self._assert_dashboard_content_exists()
        # The dashboard section's sort order must not be rewritten either.
        self.assertEqual(
            Section.objects.get(page__slug="home", label="Dashboard notice").sort_order, 99
        )

    def test_force_refresh_does_not_recreate_a_deleted_dashboard_row(self):
        News.objects.create(
            title="Temporary dashboard news",
            slug="temporary-news",
            published_at=date(2026, 11, 17),
        )
        News.objects.filter(slug="temporary-news").delete()
        call_command("seed_content", "--force-refresh", stdout=StringIO())
        self.assertFalse(News.objects.filter(slug="temporary-news").exists())

    # -- reset ----------------------------------------------------------
    def test_reset_requires_explicit_confirmation(self):
        self._add_dashboard_content()
        page_count = Page.objects.count()

        with self.assertRaises(CommandError):
            call_command("seed_content", "--reset", stdout=StringIO())

        self.assertEqual(Page.objects.count(), page_count)
        self._assert_dashboard_content_exists()

    def test_confirmed_reset_restores_seed_copy_and_keeps_dashboard_content(self):
        self._add_dashboard_content()
        section = self._home_section()
        section.html = '<p id="dashboard-edit">Edited in the dashboard</p>'
        section.save()

        call_command("seed_content", "--reset", "--confirm-reset", stdout=StringIO())

        self._assert_dashboard_content_exists()
        restored = Page.objects.get(slug="home").sections.get(label="Hero")
        self.assertNotIn("dashboard-edit", restored.html)
        self.assertIn("data-count", restored.html)

    def test_reset_and_refresh_cannot_be_combined(self):
        with self.assertRaises(CommandError):
            call_command(
                "seed_content", "--reset", "--confirm-reset", "--refresh", stdout=StringIO()
            )

    # -- settings -------------------------------------------------------
    def test_settings_entered_in_the_dashboard_survive_restore(self):
        settings_obj = SiteSetting.load()
        settings_obj.site_name = "Dashboard Site Name"
        settings_obj.seo_default_description = "Dashboard description"
        settings_obj.navigation = [{"label": "Dashboard link", "href": "/dashboard/"}]
        settings_obj.footer_columns = [{"title": "Dashboard column", "links": []}]
        settings_obj.statistics = [{"value": "9", "label": "Dashboard statistic", "animate": True}]
        settings_obj.save()

        call_command("seed_content", "--force-refresh", stdout=StringIO())

        settings_obj.refresh_from_db()
        self.assertEqual(settings_obj.site_name, "Dashboard Site Name")
        self.assertEqual(settings_obj.seo_default_description, "Dashboard description")
        self.assertEqual(settings_obj.navigation, [{"label": "Dashboard link", "href": "/dashboard/"}])
        self.assertEqual(
            settings_obj.footer_columns, [{"title": "Dashboard column", "links": []}]
        )
        self.assertEqual(
            settings_obj.statistics,
            [{"value": "9", "label": "Dashboard statistic", "animate": True}],
        )

    # -- safety dump ----------------------------------------------------
    def test_restore_modes_write_a_safety_dump_first(self):
        Page.objects.create(slug="dashboard-page", title="Dashboard page")

        call_command("seed_content", "--force-refresh", stdout=StringIO())

        dumps = sorted(Path(self._backup_temp.name).glob("klb_preseed_*.json"))
        self.assertEqual(len(dumps), 1)
        payload = json.loads(dumps[0].read_text(encoding="utf-8"))
        page_entries = [
            entry
            for entry in payload
            if entry["model"] == "content.page" and entry["fields"].get("slug") == "dashboard-page"
        ]
        self.assertEqual(len(page_entries), 1)
        self.assertEqual(page_entries[0]["fields"]["title"], "Dashboard page")
