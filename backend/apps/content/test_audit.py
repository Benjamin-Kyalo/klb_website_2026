"""Executable end-to-end audit for the KLB website API.

Every test in this module was written for the 2026 acceptance audit and is
expected to prove a real behaviour: public content, public forms, email,
authentication, CSRF, every dashboard CRUD surface, role boundaries, expiry,
uploads, search/pagination, SEO, health and the SPA shell.

Run the whole suite with:

    python manage.py test --settings=config.test_settings

Run only this audit with:

    python manage.py test apps.content.test_audit --settings=config.test_settings
"""
import io
import json
import os
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ActivityLog, User
from apps.catalogue.models import Book
from apps.content.models import (
    Career,
    DigitalPartner,
    DropdownOption,
    News,
    Page,
    Resource,
    Section,
    SiteSetting,
    TeamPhoto,
    Tender,
    WebsiteTheme,
)
from apps.enquiries.models import Enquiry, Subscriber

PASSWORD = "StrongPass!2026"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
PDF_BYTES = b"%PDF-1.7\n" + b"0" * 32


def error_message(response):
    """Return a readable DRF payload for assertion failure messages."""
    return getattr(response, "data", None) or getattr(response, "content", b"")


def client_for(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


class AuditFixtures(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.super_admin = User.objects.create_user(
            username="audit_super",
            email="audit_super@example.com",
            password=PASSWORD,
            role=User.Role.SUPER_ADMIN,
            full_name="Audit Super",
        )
        cls.admin = User.objects.create_user(
            username="audit_admin",
            email="audit_admin@example.com",
            password=PASSWORD,
            role=User.Role.ADMINISTRATOR,
            full_name="Audit Admin",
        )
        cls.editor = User.objects.create_user(
            username="audit_editor",
            email="audit_editor@example.com",
            password=PASSWORD,
            role=User.Role.EDITOR,
            full_name="Audit Editor",
        )
        cls.suspended = User.objects.create_user(
            username="audit_suspended",
            email="audit_suspended@example.com",
            password=PASSWORD,
            role=User.Role.ADMINISTRATOR,
            is_suspended=True,
        )
        cls.inactive = User.objects.create_user(
            username="audit_inactive",
            email="audit_inactive@example.com",
            password=PASSWORD,
            role=User.Role.EDITOR,
            is_active=False,
        )

    def setUp(self):
        cache.clear()
        self.anon = APIClient()
        self.super = client_for(self.super_admin)
        self.admin_client = client_for(self.admin)
        self.editor_client = client_for(self.editor)
        self.suspended_client = client_for(self.suspended)
        self.inactive_client = client_for(self.inactive)


class PublicContentAuditTests(AuditFixtures):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        today = timezone.localdate()

        cls.page = Page.objects.create(
            slug="audit-page", title="Audit page", status=Page.Status.PUBLISHED
        )
        Section.objects.create(
            page=cls.page, label="Intro", html="<p>Hello audit</p>", sort_order=1
        )
        Section.objects.create(
            page=cls.page, label="Second", html="<p>Second block</p>", sort_order=2
        )
        Page.objects.create(
            slug="audit-draft", title="Draft page", status=Page.Status.DRAFT
        )

        cls.book = Book.objects.create(
            title="Audit Mathematics",
            category="Textbook",
            categories=["Education"],
            collection="CBE Grade 4",
            level="Grade 4",
            language="English",
            subject="Mathematics",
            description="Numbers and patterns",
            isbn="9780000000001",
            price="750.00",
            featured=True,
            new_arrival=True,
        )
        cls.book2 = Book.objects.create(
            title="Audit Reader",
            collection="Secondary Form 2",
            level="Form 2",
            language="Kiswahili",
            price=None,
        )
        cls.hidden_book = Book.objects.create(
            title="Hidden Audit Book", is_published=False
        )

        cls.news = News.objects.create(
            title="Audit announcement",
            slug="audit-announcement",
            summary="A summary for searching",
            body_html="<p>Body</p>",
            category="News",
            published_at=today,
            featured=True,
            status=News.Status.PUBLISHED,
        )
        News.objects.create(
            title="Hidden audit story",
            slug="hidden-audit-story",
            summary="Draft summary",
            published_at=today,
            status=News.Status.DRAFT,
            category="News",
        )

        cls.open_job = Career.objects.create(
            title="Open audit job", closing_date=today + timedelta(days=14)
        )
        cls.closing_job = Career.objects.create(
            title="Closing audit job", closing_date=today + timedelta(days=2)
        )
        cls.expired_job = Career.objects.create(
            title="Expired audit job", closing_date=today - timedelta(days=2)
        )
        cls.upcoming_job = Career.objects.create(
            title="Upcoming audit job", opening_date=today + timedelta(days=5)
        )
        cls.closed_job = Career.objects.create(
            title="Closed audit job", is_open=False
        )

        cls.open_tender = Tender.objects.create(
            title="Open audit tender", closing_date=today + timedelta(days=20)
        )
        cls.expired_tender = Tender.objects.create(
            title="Expired audit tender", closing_date=today - timedelta(days=1)
        )
        cls.closed_tender = Tender.objects.create(
            title="Closed audit tender", is_open=False
        )

        cls.resource = Resource.objects.create(
            title="Audit price list",
            category="Price list",
            file_url="/media/uploads/prices.pdf",
        )
        Resource.objects.create(
            title="Audit annual report",
            category="Annual report",
            file_url="/media/uploads/report.pdf",
        )

        cls.partner = DigitalPartner.objects.create(
            key="audit-partner", name="Audit partner", is_active=True, sort_order=1
        )
        DigitalPartner.objects.create(
            key="audit-hidden", name="Hidden partner", is_active=False, sort_order=2
        )

        cls.theme = WebsiteTheme.objects.create(
            name="Audit campaign",
            slug="audit-campaign",
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
            is_active=True,
        )
        WebsiteTheme.objects.create(
            name="Expired campaign",
            slug="expired-campaign",
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=1),
            is_active=True,
        )

    def test_site_endpoint_exposes_display_settings_but_not_private_ones(self):
        site = SiteSetting.load()
        site.inquiry_recipient_email = "private-inbox@example.org"
        site.backup_retention = 3
        site.maintenance_mode = False
        site.save()

        response = self.anon.get("/api/site/")

        self.assertEqual(response.status_code, 200)
        payload = response.data
        self.assertIn("settings", payload)
        self.assertIn("navigation", payload)
        self.assertIn("pages", payload)
        setting_keys = set(payload["settings"].keys())
        self.assertIn("site_name", setting_keys)
        self.assertIn("maintenance_mode", setting_keys)
        self.assertIn("statistics", setting_keys)
        self.assertNotIn("inquiry_recipient_email", setting_keys)
        self.assertNotIn("backup_retention", setting_keys)
        published_slugs = {row["slug"] for row in payload["pages"]}
        self.assertIn("audit-page", published_slugs)
        self.assertNotIn("audit-draft", published_slugs)

    def test_page_detail_requires_published_status(self):
        response = self.anon.get("/api/pages/audit-page/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([s["label"] for s in response.data["sections"]], ["Intro", "Second"])

        self.assertEqual(self.anon.get("/api/pages/audit-draft/").status_code, 404)
        self.assertEqual(self.anon.get("/api/pages/does-not-exist/").status_code, 404)

    def test_catalogue_filters_search_and_pagination(self):
        listing = self.anon.get("/api/books/")
        self.assertEqual(listing.status_code, 200)
        self.assertIn("results", listing.data)
        self.assertIn("count", listing.data)
        slugs = {row["slug"] for row in listing.data["results"]}
        self.assertIn(self.book.slug, slugs)
        self.assertNotIn(self.hidden_book.slug, slugs)

        # Collection tab labels match every grade/form prefix.
        by_collection = self.anon.get("/api/books/?collection=CBE")
        self.assertEqual(by_collection.status_code, 200)
        self.assertEqual(
            [row["title"] for row in by_collection.data["results"]], ["Audit Mathematics"]
        )

        by_category = self.anon.get("/api/books/?category=Education")
        self.assertEqual(by_category.status_code, 200)
        self.assertIn(self.book.slug, {row["slug"] for row in by_category.data["results"]})

        by_level = self.anon.get("/api/books/?level=Form%202")
        self.assertEqual(by_level.status_code, 200)
        self.assertEqual([row["slug"] for row in by_level.data["results"]], [self.book2.slug])

        featured = self.anon.get("/api/books/?featured=1&new=1")
        self.assertEqual(featured.status_code, 200)
        self.assertEqual([row["slug"] for row in featured.data["results"]], [self.book.slug])

        # SQLite uses the icontains fallback; the request must not 500.
        search = self.anon.get("/api/books/?q=Mathematics")
        self.assertEqual(search.status_code, 200, error_message(search))
        self.assertIn(self.book.slug, {row["slug"] for row in search.data["results"]})

        empty_search = self.anon.get("/api/books/?q=zzzz-no-match")
        self.assertEqual(empty_search.status_code, 200)
        self.assertEqual(empty_search.data["count"], 0)

        # Invalid ordering is ignored rather than causing an error.
        self.assertEqual(self.anon.get("/api/books/?ordering=not_a_field").status_code, 200)
        ordered = self.anon.get("/api/books/?ordering=price")
        self.assertEqual(ordered.status_code, 200)

        paginated = self.anon.get("/api/books/?page_size=1")
        self.assertEqual(paginated.status_code, 200)
        self.assertEqual(len(paginated.data["results"]), 1)
        self.assertIsNotNone(paginated.data["next"])
        self.assertEqual(self.anon.get("/api/books/?page=99").status_code, 404)

        detail = self.anon.get(f"/api/books/{self.book.slug}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["price_display"], "KES 750")
        self.assertEqual(self.anon.get(f"/api/books/{self.hidden_book.slug}/").status_code, 404)

    def test_catalogue_facets_only_contain_published_values(self):
        response = self.anon.get("/api/catalogue/filters/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Textbook", response.data["categories"])
        self.assertIn("CBE Grade 4", response.data["collections"])
        self.assertIn("English", response.data["languages"])
        self.assertNotIn("", response.data["categories"])

    def test_news_filters_search_limit_and_drafts(self):
        listing = self.anon.get("/api/news/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([row["slug"] for row in listing.data], [self.news.slug])

        self.assertEqual(len(self.anon.get("/api/news/?featured=1").data), 1)
        self.assertEqual(len(self.anon.get("/api/news/?category=News").data), 1)
        self.assertEqual(len(self.anon.get("/api/news/?category=Missing").data), 0)
        self.assertEqual(len(self.anon.get("/api/news/?q=searching").data), 1)
        self.assertEqual(len(self.anon.get("/api/news/?q=zzzz").data), 0)
        self.assertEqual(len(self.anon.get("/api/news/?limit=1").data), 1)

        detail = self.anon.get(f"/api/news/{self.news.slug}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["title"], "Audit announcement")
        self.assertEqual(self.anon.get("/api/news/hidden-audit-story/").status_code, 404)

    def test_careers_expiry_status_and_open_filter(self):
        response = self.anon.get("/api/careers/")
        self.assertEqual(response.status_code, 200)
        titles = {row["title"]: row for row in response.data}
        self.assertIn("Open audit job", titles)
        self.assertIn("Expired audit job", titles)  # shown with an expired status
        self.assertNotIn("Closed audit job", titles)
        self.assertEqual(titles["Open audit job"]["status"], "open")
        self.assertEqual(titles["Closing audit job"]["status"], "closing_soon")
        self.assertEqual(titles["Expired audit job"]["status"], "expired")
        self.assertEqual(titles["Upcoming audit job"]["status"], "upcoming")

        all_rows = self.anon.get("/api/careers/?all=1")
        self.assertEqual(all_rows.status_code, 200)
        self.assertIn("Closed audit job", {row["title"] for row in all_rows.data})

    def test_tenders_expiry_status_and_open_filter(self):
        response = self.anon.get("/api/tenders/")
        self.assertEqual(response.status_code, 200)
        titles = {row["title"]: row for row in response.data}
        self.assertIn("Open audit tender", titles)
        self.assertIn("Expired audit tender", titles)
        self.assertNotIn("Closed audit tender", titles)
        self.assertEqual(titles["Open audit tender"]["status"], "open")
        self.assertEqual(titles["Expired audit tender"]["status"], "expired")

        all_rows = self.anon.get("/api/tenders/?all=1")
        self.assertIn("Closed audit tender", {row["title"] for row in all_rows.data})

    def test_resources_and_digital_partners(self):
        resources = self.anon.get("/api/resources/")
        self.assertEqual(resources.status_code, 200)
        self.assertEqual(len(resources.data), 2)
        filtered = self.anon.get("/api/resources/?category=Price%20list")
        self.assertEqual([row["title"] for row in filtered.data], ["Audit price list"])

        partners = self.anon.get("/api/digital-partners/")
        self.assertEqual(partners.status_code, 200)
        self.assertEqual([row["key"] for row in partners.data], ["audit-partner"])

    def test_active_theme_only_returns_a_theme_inside_its_window(self):
        response = self.anon.get("/api/themes/active/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Audit campaign")
        self.assertEqual(response.data["status"], "active")

        self.theme.is_active = False
        self.theme.save()
        disabled = self.anon.get("/api/themes/active/")
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(disabled.data, {"active": False})

    def test_sitemap_robots_health_and_spa(self):
        sitemap = self.anon.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        body = sitemap.content.decode("utf-8")
        self.assertIn("<urlset", body)
        self.assertIn("/audit-page/", body)
        self.assertIn(f"/books/{self.book.slug}/", body)
        self.assertIn(f"/news/{self.news.slug}/", body)
        self.assertNotIn("/audit-draft/", body)
        self.assertNotIn("hidden-audit", body)

        robots = self.anon.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        text = robots.content.decode("utf-8")
        self.assertIn("Disallow: /admin/", text)
        self.assertIn("Sitemap:", text)

        health = self.anon.get("/health/")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

        spa = self.anon.get("/some-client-side-route/")
        self.assertEqual(spa.status_code, 200)
        self.assertIn("text/html", spa["Content-Type"])

    def test_media_serving_blocks_traversal(self):
        target = Path(settings.MEDIA_ROOT) / "uploads"
        target.mkdir(parents=True, exist_ok=True)
        (target / "audit.txt").write_text("audit media", encoding="utf-8")

        served = self.anon.get("/media/uploads/audit.txt")
        self.assertEqual(served.status_code, 200)
        self.assertEqual(b"".join(served.streaming_content), b"audit media")

        for path in ("/media/../manage.py", "/media/%2e%2e/manage.py", "/media/..%2F..%2Fmanage.py"):
            response = self.anon.get(path)
            self.assertIn(response.status_code, (400, 404), f"{path} returned {response.status_code}")

    @override_settings(DEBUG=False)
    def test_security_headers_allow_the_live_chat_widget(self):
        response = self.anon.get("/health/")
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self' 'unsafe-inline' https://code.tidio.co", csp)
        # The Tidio widget needs its own webfonts, notification sound and frame.
        self.assertIn("font-src 'self' data: https://code.tidio.co", csp)
        self.assertIn("media-src 'self' https://code.tidio.co", csp)
        self.assertIn("frame-src 'self' https://code.tidio.co", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("camera=()", response["Permissions-Policy"])


class PublicFormAuditTests(AuditFixtures):
    def setUp(self):
        super().setUp()
        site = SiteSetting.load()
        site.contact_email = "contact@example.org"
        site.inquiry_recipient_email = "inquiries@example.org"
        site.save()

    def enquiry_payload(self, **overrides):
        payload = {
            "name": "Jane Mwangi",
            "email": "jane@example.com",
            "phone": "+254700000000",
            "organisation": "Audit School",
            "enquiry_type": "general",
            "subject": "Question about an order",
            "message": "Please tell me more about this textbook order.",
        }
        payload.update(overrides)
        return payload

    def test_enquiry_is_saved_and_emailed_to_the_configured_inbox(self):
        response = self.anon.post("/api/enquiries/", self.enquiry_payload(), format="json")

        self.assertEqual(response.status_code, 201, error_message(response))
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.status, Enquiry.Status.NEW)
        self.assertEqual(enquiry.internal_note, "")
        self.assertEqual(response.data["enquiry"]["subject"], "Question about an order")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["inquiries@example.org"])
        self.assertIn("Question about an order", mail.outbox[0].subject)

    def test_enquiry_email_falls_back_to_contact_email(self):
        site = SiteSetting.load()
        site.inquiry_recipient_email = ""
        site.save()

        response = self.anon.post("/api/enquiries/", self.enquiry_payload(), format="json")

        self.assertEqual(response.status_code, 201, error_message(response))
        self.assertEqual(mail.outbox[0].to, ["contact@example.org"])

    def test_enquiry_rejects_invalid_fields_and_ignores_internal_fields(self):
        invalid = [
            {"name": "J"},
            {"subject": "No"},
            {"message": "short"},
            {"message": "x" * 5001},
            {"email": "not-an-email"},
            {"enquiry_type": "not-a-real-type"},
        ]
        for overrides in invalid:
            response = self.anon.post(
                "/api/enquiries/", self.enquiry_payload(**overrides), format="json"
            )
            self.assertEqual(response.status_code, 400, f"{overrides}: {error_message(response)}")

        self.assertFalse(Enquiry.objects.exists())

        accepted = self.anon.post(
            "/api/enquiries/",
            self.enquiry_payload(status="closed", internal_note="crafted", id=999),
            format="json",
        )
        self.assertEqual(accepted.status_code, 201, error_message(accepted))
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.status, Enquiry.Status.NEW)
        self.assertEqual(enquiry.internal_note, "")
        self.assertNotEqual(enquiry.pk, 999)

    def test_enquiry_honeypot_silently_discards_bots(self):
        response = self.anon.post(
            "/api/enquiries/",
            self.enquiry_payload(company_website="https://spam.example"),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(Enquiry.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_enquiry_is_rate_limited(self):
        statuses = []
        for _ in range(11):
            statuses.append(
                self.anon.post("/api/enquiries/", self.enquiry_payload(), format="json").status_code
            )
        self.assertEqual(statuses[:10], [201] * 10)
        self.assertEqual(statuses[10], 429)

    def test_newsletter_subscribe_flow(self):
        first = self.anon.post("/api/newsletter/", {"email": "Reader@Example.com"}, format="json")
        self.assertEqual(first.status_code, 201, error_message(first))
        subscriber = Subscriber.objects.get()
        self.assertEqual(subscriber.email, "reader@example.com")
        self.assertTrue(subscriber.is_active)

        duplicate = self.anon.post("/api/newsletter/", {"email": "reader@example.com"}, format="json")
        self.assertEqual(duplicate.status_code, 200, error_message(duplicate))
        self.assertTrue(duplicate.data["already_subscribed"])

        invalid = self.anon.post("/api/newsletter/", {"email": "not-an-email"}, format="json")
        self.assertEqual(invalid.status_code, 400)
        missing = self.anon.post("/api/newsletter/", {}, format="json")
        self.assertEqual(missing.status_code, 400)

    def test_newsletter_unsubscribe_and_resubscribe_flow(self):
        subscriber = Subscriber.objects.create(email="reader@example.com", is_active=True)

        unsubscribe = self.anon.post(
            "/api/newsletter/unsubscribe/", {"email": "reader@example.com"}, format="json"
        )
        self.assertEqual(unsubscribe.status_code, 200, error_message(unsubscribe))
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)

        again = self.anon.post(
            "/api/newsletter/unsubscribe/", {"email": "reader@example.com"}, format="json"
        )
        self.assertEqual(again.status_code, 200)

        missing_address = self.anon.post(
            "/api/newsletter/unsubscribe/", {"email": "nobody@example.com"}, format="json"
        )
        self.assertEqual(missing_address.status_code, 404)
        blank = self.anon.post("/api/newsletter/unsubscribe/", {}, format="json")
        self.assertEqual(blank.status_code, 400)

        resubscribed = self.anon.post(
            "/api/newsletter/", {"email": "reader@example.com"}, format="json"
        )
        self.assertEqual(resubscribed.status_code, 201, error_message(resubscribed))
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)

    def test_newsletter_is_rate_limited(self):
        statuses = []
        for index in range(6):
            statuses.append(
                self.anon.post(
                    "/api/newsletter/", {"email": f"rate{index}@example.com"}, format="json"
                ).status_code
            )
        self.assertEqual(statuses[:5], [201] * 5)
        self.assertEqual(statuses[5], 429)


class AuthenticationAuditTests(AuditFixtures):
    def test_csrf_token_endpoint_sets_cookie(self):
        client = APIClient()
        response = client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["csrfToken"])
        self.assertIn("csrftoken", client.cookies)

    def test_login_requires_a_valid_csrf_token(self):
        # The default test client silently disables CSRF. Turn it back on so
        # this exercises the same path a real browser takes.
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            "/api/auth/login/",
            {"email": self.editor.email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 403, error_message(response))

    def login(self, email, password=PASSWORD):
        client = APIClient()
        token = client.get("/api/auth/csrf/").data["csrfToken"]
        response = client.post(
            "/api/auth/login/",
            {"email": email, "password": password},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        return client, response

    def test_login_me_logout_and_wrong_password(self):
        client, bad = self.login(self.editor.email, "WrongPassword!9")
        self.assertEqual(bad.status_code, 400)

        client, good = self.login(self.editor.email)
        self.assertEqual(good.status_code, 200, error_message(good))
        self.assertEqual(good.data["user"]["email"], self.editor.email)

        me = client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["user"]["email"], self.editor.email)

        logout = client.post(
            "/api/auth/logout/",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertEqual(logout.status_code, 200, error_message(logout))
        self.assertIsNone(client.get("/api/auth/me/").data["user"])

    def test_suspended_and_inactive_accounts_are_blocked(self):
        for email in (self.suspended.email, self.inactive.email):
            _client, response = self.login(email)
            self.assertEqual(response.status_code, 400, f"{email}: {error_message(response)}")

        self.assertIsNone(self.suspended_client.get("/api/auth/me/").data["user"])
        self.assertIsNone(self.inactive_client.get("/api/auth/me/").data["user"])
        self.assertEqual(self.suspended_client.get("/api/admin/stats/").status_code, 403)
        self.assertEqual(self.inactive_client.get("/api/admin/stats/").status_code, 403)

    def test_login_is_rate_limited(self):
        client = APIClient()
        token = client.get("/api/auth/csrf/").data["csrfToken"]
        statuses = []
        for _ in range(6):
            statuses.append(
                client.post(
                    "/api/auth/login/",
                    {"email": self.editor.email, "password": "WrongPassword!9"},
                    format="json",
                    HTTP_X_CSRFTOKEN=token,
                ).status_code
            )
        self.assertEqual(statuses[:5], [400] * 5)
        self.assertEqual(statuses[5], 429)

    def test_password_change_validation_and_success(self):
        client = client_for(self.editor)
        wrong = client.post(
            "/api/auth/password/",
            {"current_password": "WrongPassword!9", "new_password": "AnotherPass!2026"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)

        short = client.post(
            "/api/auth/password/",
            {"current_password": PASSWORD, "new_password": "short"},
            format="json",
        )
        self.assertEqual(short.status_code, 400)

        changed = client.post(
            "/api/auth/password/",
            {"current_password": PASSWORD, "new_password": "AnotherPass!2026"},
            format="json",
        )
        self.assertEqual(changed.status_code, 200, error_message(changed))
        self.editor.refresh_from_db()
        self.assertTrue(self.editor.check_password("AnotherPass!2026"))
        self.assertTrue(
            ActivityLog.objects.filter(action=ActivityLog.Action.PASSWORD, actor=self.editor).exists()
        )


class AdminCrudAuditTests(AuditFixtures):
    def test_page_crud_sections_and_duplicate(self):
        payload = {
            "slug": "audit-created-page",
            "title": "Created audit page",
            "status": "published",
            "sections": [{"label": "Body", "html": "<p>Created</p>", "settings": {"x": 1}}],
        }
        created = self.super.post("/api/admin/pages/", payload, format="json")
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(created.data["slug"], "audit-created-page")
        self.assertEqual(created.data["sections"][0]["label"], "Body")

        listing = self.super.get("/api/admin/pages/?search=Created")
        self.assertEqual(listing.status_code, 200)
        self.assertIn("audit-created-page", {row["slug"] for row in listing.data["results"]})

        detail = self.super.get("/api/admin/pages/audit-created-page/")
        self.assertEqual(detail.status_code, 200)

        patched = self.super.patch(
            "/api/admin/pages/audit-created-page/",
            {"title": "Renamed audit page", "sections": [{"label": "Only", "html": "<p>Only</p>"}]},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))
        self.assertEqual(patched.data["title"], "Renamed audit page")
        self.assertEqual(len(patched.data["sections"]), 1)

        duplicate = self.super.post("/api/admin/pages/audit-created-page/duplicate/")
        self.assertEqual(duplicate.status_code, 201, error_message(duplicate))
        self.assertEqual(duplicate.data["status"], "draft")
        self.assertTrue(duplicate.data["slug"].startswith("audit-created-page-copy"))

        deleted = self.super.delete("/api/admin/pages/audit-created-page/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.super.get("/api/admin/pages/audit-created-page/").status_code, 404)
        self.assertTrue(
            ActivityLog.objects.filter(module="pages", action=ActivityLog.Action.DELETE).exists()
        )

    def test_editor_cannot_publish_or_delete_pages(self):
        created = self.editor_client.post(
            "/api/admin/pages/",
            {
                "slug": "editor-page",
                "title": "Editor page",
                "status": "published",
                "sections": [],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(created.data["status"], "draft")

        published = self.editor_client.patch(
            "/api/admin/pages/editor-page/", {"status": "published"}, format="json"
        )
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data["status"], "draft")

        self.assertEqual(self.editor_client.delete("/api/admin/pages/editor-page/").status_code, 403)

    def test_book_crud_generates_unique_slugs_and_searches(self):
        first = self.super.post(
            "/api/admin/books/", {"title": "Audit Book Duplicate"}, format="json"
        )
        self.assertEqual(first.status_code, 201, error_message(first))
        self.assertEqual(first.data["slug"], "audit-book-duplicate")

        second = self.super.post(
            "/api/admin/books/", {"title": "Audit Book Duplicate"}, format="json"
        )
        self.assertEqual(second.status_code, 201, error_message(second))
        self.assertEqual(second.data["slug"], "audit-book-duplicate-2")

        clash = self.super.post(
            "/api/admin/books/",
            {"title": "Explicit clash", "slug": "audit-book-duplicate"},
            format="json",
        )
        self.assertEqual(clash.status_code, 400, error_message(clash))

        search = self.anon.get("/api/books/?q=Audit Book Duplicate")
        self.assertEqual(search.status_code, 200, error_message(search))
        self.assertGreaterEqual(search.data["count"], 2)

        patched = self.super.patch(
            f"/api/admin/books/{first.data['slug']}/",
            {"price": "1250.00", "featured": True},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))
        self.assertEqual(patched.data["price_display"], "KES 1,250")

        public = self.anon.get(f"/api/books/{first.data['slug']}/")
        self.assertEqual(public.status_code, 200)

        self.assertEqual(
            self.super.delete(f"/api/admin/books/{first.data['slug']}/").status_code, 204
        )
        self.assertEqual(self.anon.get(f"/api/books/{first.data['slug']}/").status_code, 404)

    def test_unpublished_book_is_hidden_from_the_public_api(self):
        created = self.super.post(
            "/api/admin/books/",
            {"title": "Secret audit title", "is_published": False},
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(self.anon.get(f"/api/books/{created.data['slug']}/").status_code, 404)

    def test_news_crud_and_slug_rules(self):
        payload = {
            "title": "Created audit news",
            "summary": "Summary",
            "body_html": "<p>Body</p>",
            "published_at": timezone.localdate().isoformat(),
            "status": "published",
        }
        created = self.super.post("/api/admin/news/", payload, format="json")
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(created.data["slug"], "created-audit-news")

        second = self.super.post("/api/admin/news/", payload, format="json")
        self.assertEqual(second.status_code, 201, error_message(second))
        self.assertEqual(second.data["slug"], "created-audit-news-2")

        clash = self.super.post(
            "/api/admin/news/",
            {**payload, "slug": "created-audit-news"},
            format="json",
        )
        self.assertEqual(clash.status_code, 400, error_message(clash))

        patched = self.super.patch(
            f"/api/admin/news/{created.data['slug']}/",
            {"title": "Renamed audit news"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))

        self.assertEqual(
            self.super.delete(f"/api/admin/news/{created.data['slug']}/").status_code, 204
        )

    def test_careers_crud(self):
        today = timezone.localdate()
        created = self.super.post(
            "/api/admin/careers/",
            {
                "title": "Created audit career",
                "closing_date": (today + timedelta(days=10)).isoformat(),
                "is_open": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(created.data["status"], "open")

        patched = self.super.patch(
            f"/api/admin/careers/{created.data['id']}/",
            {"is_open": False},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))
        self.assertNotIn(
            "Created audit career",
            {row["title"] for row in self.anon.get("/api/careers/").data},
        )
        self.assertIn(
            "Created audit career",
            {row["title"] for row in self.anon.get("/api/careers/?all=1").data},
        )
        self.assertEqual(
            self.super.delete(f"/api/admin/careers/{created.data['id']}/").status_code, 204
        )

    def test_tenders_crud(self):
        created = self.super.post(
            "/api/admin/tenders/",
            {"title": "Created audit tender", "category": "Goods", "is_open": True},
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(created.data["status"], "open")

        bad_link = self.super.patch(
            f"/api/admin/tenders/{created.data['id']}/",
            {"document_url": "assets\\docs\\notice.pdf"},
            format="json",
        )
        self.assertEqual(bad_link.status_code, 400, error_message(bad_link))
        self.assertIn("document_url", bad_link.data["errors"])

        good_link = self.super.patch(
            f"/api/admin/tenders/{created.data['id']}/",
            {"document_url": "/assets/docs/notice.pdf"},
            format="json",
        )
        self.assertEqual(good_link.status_code, 200, error_message(good_link))
        self.assertEqual(good_link.data["document_url"], "/assets/docs/notice.pdf")

        retried = self.super.get(f"/api/admin/tenders/{created.data['id']}/")
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(
            self.super.delete(f"/api/admin/tenders/{created.data['id']}/").status_code, 204
        )

    def test_resources_crud(self):
        created = self.super.post(
            "/api/admin/resources/",
            {
                "title": "Created audit resource",
                "category": "Form",
                "file_url": "/media/uploads/form.pdf",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))

        bad_link = self.super.patch(
            f"/api/admin/resources/{created.data['id']}/",
            {"file_url": "assets\\docs\\form.pdf"},
            format="json",
        )
        self.assertEqual(bad_link.status_code, 400, error_message(bad_link))
        self.assertIn("file_url", bad_link.data["errors"])

        good_link = self.super.patch(
            f"/api/admin/resources/{created.data['id']}/",
            {"file_url": "https://example.org/form.pdf"},
            format="json",
        )
        self.assertEqual(good_link.status_code, 200, error_message(good_link))
        self.assertEqual(good_link.data["file_url"], "https://example.org/form.pdf")

        patched = self.super.patch(
            f"/api/admin/resources/{created.data['id']}/",
            {"external": True},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))
        self.assertEqual(
            self.super.delete(f"/api/admin/resources/{created.data['id']}/").status_code, 204
        )

    def test_digital_partners_crud_and_public_visibility(self):
        created = self.super.post(
            "/api/admin/digital-partners/",
            {"key": "created-partner", "name": "Created partner", "is_active": False},
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertNotIn(
            "created-partner",
            {row["key"] for row in self.anon.get("/api/digital-partners/").data},
        )

        patched = self.super.patch(
            f"/api/admin/digital-partners/{created.data['id']}/",
            {"is_active": True},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))
        self.assertIn(
            "created-partner",
            {row["key"] for row in self.anon.get("/api/digital-partners/").data},
        )
        self.assertEqual(
            self.super.delete(f"/api/admin/digital-partners/{created.data['id']}/").status_code,
            204,
        )

    def test_themes_crud_slug_generation_and_active_window(self):
        today = timezone.localdate()
        created = self.super.post(
            "/api/admin/themes/",
            {
                "name": "Created audit campaign",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=10)).isoformat(),
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(created.data["slug"], "created-audit-campaign")

        second = self.super.post(
            "/api/admin/themes/", {"name": "Created audit campaign"}, format="json"
        )
        self.assertEqual(second.status_code, 201, error_message(second))
        self.assertEqual(second.data["slug"], "created-audit-campaign-2")

        clash = self.super.post(
            "/api/admin/themes/",
            {"name": "Another theme", "slug": "created-audit-campaign"},
            format="json",
        )
        self.assertEqual(clash.status_code, 400, error_message(clash))

        active = self.anon.get("/api/themes/active/")
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.data["name"], "Created audit campaign")

        self.assertEqual(
            self.super.delete(f"/api/admin/themes/{created.data['id']}/").status_code, 204
        )

    def test_team_photo_listing_update_and_validation(self):
        about = Page.objects.create(slug="about", title="About audit")
        Section.objects.create(
            page=about,
            label="Leadership",
            html=(
                '<article class="team-card" data-member="GO">'
                '<div class="team-card__photo">GO</div>'
                "<h3>Grace Omondi</h3>"
                '<p class="team-card__role">Managing Director</p>'
                "</article>"
            ),
        )

        listing = self.super.get("/api/admin/team-photos/")
        self.assertEqual(listing.status_code, 200, error_message(listing))
        self.assertTrue(listing.data["section_found"])
        self.assertEqual(listing.data["members"][0]["key"], "GO")

        saved = self.super.patch(
            "/api/admin/team-photos/GO/",
            {"photo": "/media/uploads/grace.png"},
            format="json",
        )
        self.assertEqual(saved.status_code, 200, error_message(saved))
        self.assertTrue(TeamPhoto.objects.filter(key="GO", photo="/media/uploads/grace.png").exists())

        rejected = self.super.patch(
            "/api/admin/team-photos/GO/",
            {"photo": "javascript:alert(1)"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(
            self.super.patch(
                "/api/admin/team-photos/NOPE/", {"photo": ""}, format="json"
            ).status_code,
            404,
        )

        public = self.anon.get("/api/pages/about/")
        self.assertIn("/media/uploads/grace.png", public.data["sections"][0]["html"])

    def test_dropdown_options_crud_groups_and_duplicate_guard(self):
        created = self.super.post(
            "/api/admin/options/",
            {"group": "news_category", "label": "Audit category"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        self.assertEqual(created.data["value"], "audit-category")

        duplicate = self.super.post(
            "/api/admin/options/",
            {"group": "news_category", "label": "Audit category"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, error_message(duplicate))

        groups = self.editor_client.get("/api/admin/options/groups/")
        self.assertEqual(groups.status_code, 200, error_message(groups))
        self.assertIn("news_category", groups.data["options"])

        self.assertEqual(self.editor_client.get("/api/admin/options/").status_code, 403)
        self.assertEqual(
            self.super.delete(f"/api/admin/options/{created.data['id']}/").status_code, 204
        )

    def test_settings_permissions_and_test_email_endpoint(self):
        patched = self.admin_client.patch(
            "/api/admin/settings/", {"phone": "020 000 0000"}, format="json"
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))
        self.assertEqual(SiteSetting.load().phone, "020 000 0000")

        critical = self.admin_client.patch(
            "/api/admin/settings/", {"navigation": [{"label": "Hacked"}]}, format="json"
        )
        self.assertEqual(critical.status_code, 403, error_message(critical))
        self.assertEqual(self.editor_client.get("/api/admin/settings/").status_code, 403)
        self.assertEqual(
            self.admin_client.patch(
                "/api/admin/settings/", {"navigation": "not-a-list"}, format="json"
            ).status_code,
            403,
        )
        allowed = self.super.patch(
            "/api/admin/settings/", {"navigation": [{"label": "Home"}]}, format="json"
        )
        self.assertEqual(allowed.status_code, 200, error_message(allowed))
        invalid = self.super.patch(
            "/api/admin/settings/", {"navigation": "not-a-list"}, format="json"
        )
        self.assertEqual(invalid.status_code, 400)

        site = SiteSetting.load()
        site.inquiry_recipient_email = "audit-inbox@example.org"
        site.save()
        test_email = self.admin_client.post("/api/admin/settings/test-inquiry-email/")
        self.assertEqual(test_email.status_code, 200, error_message(test_email))
        self.assertIn("audit-inbox@example.org", test_email.data["detail"])
        self.assertIn("No real email was delivered", test_email.data["detail"])
        self.assertEqual(mail.outbox[-1].to, ["audit-inbox@example.org"])

        site.inquiry_recipient_email = ""
        site.contact_email = ""
        site.save()
        missing = self.admin_client.post("/api/admin/settings/test-inquiry-email/")
        self.assertEqual(missing.status_code, 400)

    def test_stats_are_filtered_by_module_permission(self):
        limited = User.objects.create_user(
            username="audit_limited",
            email="audit_limited@example.com",
            password=PASSWORD,
            role=User.Role.EDITOR,
            permissions={"pages": ["view"]},
        )
        response = client_for(limited).get("/api/admin/stats/")
        self.assertEqual(response.status_code, 200, error_message(response))
        self.assertIsNotNone(response.data["pages"])
        self.assertIsNone(response.data["books"])
        self.assertIsNone(response.data["new_enquiries"])
        self.assertIsNone(response.data["subscribers"])

    def test_user_management_boundaries(self):
        self.assertEqual(self.editor_client.get("/api/admin/users/").status_code, 403)

        admin_list = self.admin_client.get("/api/admin/users/")
        self.assertEqual(admin_list.status_code, 200)
        listed_roles = {row["role"] for row in admin_list.data["results"]}
        self.assertNotIn(User.Role.SUPER_ADMIN, listed_roles)
        self.assertIn(User.Role.ADMINISTRATOR, listed_roles)  # the admin sees themself

        created = self.admin_client.post(
            "/api/admin/users/",
            {
                "email": "created_editor@example.com",
                "full_name": "Created Editor",
                "role": "editor",
                "password": "CreatedPass!2026",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        created_user = User.objects.get(email="created_editor@example.com")
        self.assertTrue(created_user.is_staff)

        escalation = self.admin_client.post(
            "/api/admin/users/",
            {
                "email": "created_admin@example.com",
                "role": "admin",
                "password": "CreatedPass!2026",
            },
            format="json",
        )
        self.assertEqual(escalation.status_code, 400, error_message(escalation))

        missing_password = self.super.post(
            "/api/admin/users/", {"email": "no_password@example.com"}, format="json"
        )
        self.assertEqual(missing_password.status_code, 400)
        duplicate = self.super.post(
            "/api/admin/users/",
            {
                "email": created_user.email,
                "role": "editor",
                "password": "CreatedPass!2026",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)

        reset = self.super.post(
            f"/api/admin/users/{created_user.pk}/reset-password/",
            {"new_password": "ResetPass!2026"},
            format="json",
        )
        self.assertEqual(reset.status_code, 200, error_message(reset))
        created_user.refresh_from_db()
        self.assertTrue(created_user.check_password("ResetPass!2026"))

        short_reset = self.super.post(
            f"/api/admin/users/{created_user.pk}/reset-password/",
            {"new_password": "short"},
            format="json",
        )
        self.assertEqual(short_reset.status_code, 400)

        self.assertEqual(
            self.admin_client.post(
                f"/api/admin/users/{self.super_admin.pk}/reset-password/",
                {"new_password": "ResetPass!2026"},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.super.delete(f"/api/admin/users/{self.super_admin.pk}/").status_code, 400
        )
        self.assertEqual(
            self.super.delete(f"/api/admin/users/{created_user.pk}/").status_code, 204
        )

    def test_editor_permissions_are_clamped_when_saved(self):
        created = self.admin_client.post(
            "/api/admin/users/",
            {
                "email": "clamped_editor@example.com",
                "role": "editor",
                "password": "CreatedPass!2026",
                "permissions": {
                    "pages": ["view", "create", "delete", "publish"],
                    "settings": ["view", "edit"],
                    "users": ["view", "delete"],
                },
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, error_message(created))
        user = User.objects.get(email="clamped_editor@example.com")
        # The explicit grants survive for editor modules. Every other module is
        # stored with an empty list, so a crafted request cannot widen access.
        self.assertEqual(
            user.permissions["pages"], ["view", "create", "delete", "publish"]
        )
        for module in ("books", "news", "careers", "tenders", "resources",
                       "enquiries", "subscribers", "media"):
            self.assertEqual(user.permissions[module], [], module)
        # System modules are present but empty, never granted.
        for module in ("settings", "users", "activity", "backup", "options"):
            self.assertEqual(user.permissions[module], [], module)

    def test_activity_log_filters_actors_and_exports(self):
        ActivityLog.objects.create(
            actor=self.admin, actor_name="Audit Admin", actor_email=self.admin.email,
            action=ActivityLog.Action.UPDATE, module="pages", object_label="Page",
            detail="Updated page.",
        )
        ActivityLog.objects.create(
            actor=self.editor, actor_name="Audit Editor", actor_email=self.editor.email,
            action=ActivityLog.Action.CREATE, module="books", object_label="Book",
            detail="Created book.",
        )

        listing = self.super.get("/api/admin/activity/")
        self.assertEqual(listing.status_code, 200)
        self.assertGreaterEqual(listing.data["count"], 2)

        filtered = self.super.get("/api/admin/activity/?module=pages&action=update")
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(
            {row["module"] for row in filtered.data["results"]}, {"pages"}
        )

        actors = self.super.get("/api/admin/activity/actors/")
        self.assertEqual(actors.status_code, 200)
        self.assertGreaterEqual(len(actors.data), 2)

        csv_export = self.super.get("/api/admin/activity/export/?format=csv")
        self.assertEqual(csv_export.status_code, 200, error_message(csv_export))
        self.assertIn("text/csv", csv_export["Content-Type"])
        self.assertIn("attachment;", csv_export["Content-Disposition"])

        xlsx_export = self.super.get("/api/admin/activity/export/?format=xlsx")
        self.assertEqual(xlsx_export.status_code, 200, error_message(xlsx_export))
        self.assertTrue(xlsx_export.content.startswith(b"PK"))

        pdf_export = self.super.get("/api/admin/activity/export/?format=pdf")
        self.assertEqual(pdf_export.status_code, 200, error_message(pdf_export))
        self.assertTrue(pdf_export.content.startswith(b"%PDF"))

        invalid = self.super.get("/api/admin/activity/export/?format=docx")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.editor_client.get("/api/admin/activity/").status_code, 403)

    def test_upload_validation_and_permissions(self):
        valid = self.super.post(
            "/api/admin/upload/",
            {"file": SimpleUploadedFile("cover.png", PNG_BYTES, content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(valid.status_code, 201, error_message(valid))
        saved = Path(settings.MEDIA_ROOT) / valid.data["url"].removeprefix("/media/")
        self.assertTrue(saved.is_file())

        pdf = self.super.post(
            "/api/admin/upload/",
            {"file": SimpleUploadedFile("notice.pdf", PDF_BYTES, content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(pdf.status_code, 201, error_message(pdf))

        disguised = self.super.post(
            "/api/admin/upload/",
            {"file": SimpleUploadedFile("evil.png", b"<html>not an image</html>")},
            format="multipart",
        )
        self.assertEqual(disguised.status_code, 400, error_message(disguised))

        executable = self.super.post(
            "/api/admin/upload/",
            {"file": SimpleUploadedFile("payload.exe", b"MZ")},
            format="multipart",
        )
        self.assertEqual(executable.status_code, 400)

        missing = self.super.post("/api/admin/upload/", {}, format="multipart")
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(
            self.anon.post(
                "/api/admin/upload/",
                {"file": SimpleUploadedFile("anon.png", PNG_BYTES)},
                format="multipart",
            ).status_code,
            403,
        )

        too_big = self.super.post(
            "/api/admin/upload/",
            {
                "file": SimpleUploadedFile(
                    "huge.png", b"\x89PNG\r\n\x1a\n" + b"0" * (8 * 1024 * 1024)
                )
            },
            format="multipart",
        )
        self.assertEqual(too_big.status_code, 400)

        editor_upload = self.editor_client.post(
            "/api/admin/upload/",
            {"file": SimpleUploadedFile("editor.png", PNG_BYTES)},
            format="multipart",
        )
        self.assertEqual(editor_upload.status_code, 201, error_message(editor_upload))

    def test_ai_draft_requires_a_key_and_a_topic_and_parses_a_response(self):
        empty_keys = {
            "OPENAI_API_KEY": "",
            "EDENAI_API_KEY": "",
            "GROQ_API_KEY": "",
            "GEMINI_API_KEY": "",
            "OPENROUTER_API_KEY": "",
        }
        with patch.dict(os.environ, empty_keys, clear=False):
            no_key = self.super.post("/api/admin/ai-draft/", {"topic": "Audit"}, format="json")
        self.assertEqual(no_key.status_code, 503, error_message(no_key))

        with patch.dict(os.environ, {**empty_keys, "OPENAI_API_KEY": "sk-test-key"}, clear=False):
            no_topic = self.super.post("/api/admin/ai-draft/", {}, format="json")
            self.assertEqual(no_topic.status_code, 400)

            body = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "Audit headline",
                                    "summary": "A useful audit summary for the article.",
                                    "body_html": "<p>First paragraph.</p><p>Second paragraph.</p>",
                                }
                            )
                        }
                    }
                ]
            }
            response = MagicMock()
            response.read.return_value = json.dumps(body).encode("utf-8")
            response.__enter__.return_value = response
            response.__exit__.return_value = False
            with patch("urllib.request.urlopen", return_value=response):
                drafted = self.super.post(
                    "/api/admin/ai-draft/", {"topic": "Audit"}, format="json"
                )
        self.assertEqual(drafted.status_code, 200, error_message(drafted))
        self.assertEqual(drafted.data["draft"]["title"], "Audit headline")

    def test_ai_draft_reports_upstream_errors_without_crashing(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}, clear=False):
            error = HTTPError(
                "https://api.openai.com/v1/chat/completions",
                401,
                "Unauthorized",
                {},
                io.BytesIO(b'{"error":"invalid key"}'),
            )
            with patch("urllib.request.urlopen", side_effect=error):
                response = self.super.post(
                    "/api/admin/ai-draft/", {"topic": "Audit"}, format="json"
                )
        self.assertEqual(response.status_code, 502, error_message(response))

    def test_backup_lifecycle_through_the_api(self):
        created = self.super.post(
            "/api/admin/backup/", {"components": ["database"]}, format="json"
        )
        self.assertEqual(created.status_code, 200, error_message(created))
        backup_id = created.data["id"]

        listing = self.super.get("/api/admin/backup/")
        self.assertEqual(listing.status_code, 200)
        self.assertIn(backup_id, {row["id"] for row in listing.data})

        download = self.super.get(f"/api/admin/backup/{backup_id}/download/")
        self.assertEqual(download.status_code, 200)
        payload = b"".join(download.streaming_content)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(payload)))

        deleted = self.super.delete(f"/api/admin/backup/{backup_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            self.super.get(f"/api/admin/backup/{backup_id}/download/").status_code, 404
        )

    def test_backup_endpoints_require_permission(self):
        self.assertEqual(self.editor_client.get("/api/admin/backup/").status_code, 403)
        self.assertEqual(self.editor_client.post("/api/admin/backup/", {}, format="json").status_code, 403)

    def test_subscriber_management_and_enquiries_delete(self):
        subscriber = Subscriber.objects.create(email="manage@example.com")
        listing = self.admin_client.get("/api/admin/subscribers/")
        self.assertEqual(listing.status_code, 200)
        self.assertIn("manage@example.com", {row["email"] for row in listing.data["results"]})

        self.assertEqual(self.editor_client.delete(f"/api/admin/subscribers/{subscriber.pk}/").status_code, 403)
        self.assertEqual(self.admin_client.delete(f"/api/admin/subscribers/{subscriber.pk}/").status_code, 204)

        enquiry = Enquiry.objects.create(
            name="Audit Person",
            email="audit@example.com",
            subject="Audit subject",
            message="This is a long enough audit enquiry message.",
        )
        listing = self.admin_client.get("/api/admin/enquiries/?status=new&search=Audit")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)

        patched = self.admin_client.patch(
            f"/api/admin/enquiries/{enquiry.pk}/",
            {"status": "in_progress", "internal_note": "Called back."},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, error_message(patched))
        self.assertEqual(patched.data["status"], "in_progress")

        self.assertEqual(self.editor_client.patch(
            f"/api/admin/enquiries/{enquiry.pk}/", {"status": "closed"}, format="json"
        ).status_code, 403)
        self.assertEqual(self.editor_client.delete(f"/api/admin/enquiries/{enquiry.pk}/").status_code, 403)
        self.assertEqual(self.admin_client.delete(f"/api/admin/enquiries/{enquiry.pk}/").status_code, 204)
        self.assertFalse(Enquiry.objects.filter(pk=enquiry.pk).exists())


class SecurityBoundaryAuditTests(AuditFixtures):
    ADMIN_GET_PATHS = [
        "/api/admin/stats/",
        "/api/admin/settings/",
        "/api/admin/pages/",
        "/api/admin/books/",
        "/api/admin/news/",
        "/api/admin/careers/",
        "/api/admin/tenders/",
        "/api/admin/resources/",
        "/api/admin/enquiries/",
        "/api/admin/subscribers/",
        "/api/admin/users/",
        "/api/admin/activity/",
        "/api/admin/backup/",
        "/api/admin/options/",
        "/api/admin/options/groups/",
        "/api/admin/permissions/",
        "/api/admin/team-photos/",
        "/api/admin/digital-partners/",
        "/api/admin/themes/",
    ]

    def test_anonymous_cannot_read_or_write_the_dashboard(self):
        for path in self.ADMIN_GET_PATHS:
            response = self.anon.get(path)
            self.assertIn(response.status_code, (401, 403), f"{path}: {response.status_code}")
        self.assertEqual(
            self.anon.patch("/api/admin/settings/", {"phone": "x"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.anon.post("/api/admin/pages/", {"title": "x"}, format="json").status_code, 403
        )

    def test_editor_can_read_content_but_not_system_modules(self):
        readable = [
            "/api/admin/stats/",
            "/api/admin/pages/",
            "/api/admin/books/",
            "/api/admin/news/",
            "/api/admin/careers/",
            "/api/admin/tenders/",
            "/api/admin/resources/",
            "/api/admin/enquiries/",
            "/api/admin/subscribers/",
            "/api/admin/team-photos/",
            "/api/admin/digital-partners/",
            "/api/admin/themes/",
            "/api/admin/options/groups/",
        ]
        for path in readable:
            response = self.editor_client.get(path)
            self.assertEqual(response.status_code, 200, f"{path}: {error_message(response)}")

        forbidden = [
            "/api/admin/settings/",
            "/api/admin/users/",
            "/api/admin/activity/",
            "/api/admin/backup/",
            "/api/admin/options/",
            "/api/admin/permissions/",
        ]
        for path in forbidden:
            self.assertEqual(
                self.editor_client.get(path).status_code, 403, f"{path} was allowed"
            )

        self.assertEqual(
            self.editor_client.post(
                "/api/admin/books/", {"title": "Editor book"}, format="json"
            ).status_code,
            201,
        )
        self.assertEqual(
            self.editor_client.patch(
                f"/api/admin/books/{self.editor_client.get('/api/admin/books/').data['results'][0]['slug']}/",
                {"title": "Changed"},
                format="json",
            ).status_code,
            200,
        )

    def test_permission_metadata_only_for_administrators(self):
        self.assertEqual(self.editor_client.get("/api/admin/users/permissions/").status_code, 403)
        response = self.admin_client.get("/api/admin/users/permissions/")
        self.assertEqual(response.status_code, 200, error_message(response))
        self.assertIn("modules", response.data)
        self.assertFalse(response.data["canManageSuperAdmins"])
        self.assertEqual(
            self.super.get("/api/admin/users/permissions/").data["canManageSuperAdmins"], True
        )

    def test_public_settings_never_include_staff_only_values(self):
        site = SiteSetting.load()
        site.inquiry_recipient_email = "hidden@example.org"
        site.backup_retention = 99
        site.save()
        payload = self.anon.get("/api/site/").data["settings"]
        self.assertNotIn("hidden@example.org", json.dumps(payload))
        self.assertNotIn("backup_retention", payload)
        admin_payload = self.admin_client.get("/api/admin/settings/").data
        self.assertEqual(admin_payload["inquiry_recipient_email"], "hidden@example.org")
        self.assertEqual(admin_payload["backup_retention"], 99)

    def test_csrf_is_enforced_for_session_writes(self):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/auth/csrf/").data["csrfToken"]
        login = client.post(
            "/api/auth/login/",
            {"email": self.super_admin.email, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(login.status_code, 200, error_message(login))

        # Django rotates the token on login, so read the fresh one.
        token = client.get("/api/auth/csrf/").data["csrfToken"]
        without_token = client.patch(
            "/api/admin/settings/", {"phone": "020 111 1111"}, format="json"
        )
        self.assertEqual(without_token.status_code, 403, error_message(without_token))

        with_token = client.patch(
            "/api/admin/settings/",
            {"phone": "020 111 1111"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(with_token.status_code, 200, error_message(with_token))
        self.assertEqual(SiteSetting.load().phone, "020 111 1111")
