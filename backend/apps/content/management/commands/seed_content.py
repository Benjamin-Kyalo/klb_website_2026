"""Seed the KLB website with verified content.

Usage:
    python manage.py seed_content                        # create anything missing
    python manage.py seed_content --refresh              # create anything missing (deploy-safe)
    python manage.py seed_content --force-refresh        # restore the seed copy in place
    python manage.py seed_content --reset --confirm-reset  # same, with explicit confirmation

Nothing entered in the dashboard is ever deleted or overwritten. Every flag
creates missing rows only, except the explicit restore modes
(``--force-refresh`` and ``--reset --confirm-reset``), which rewrite seed-origin
pages, sections and news in place. Sections added in the dashboard carry a
blank ``seed_key`` and are never touched. Other dashboard-created rows (news,
careers, tenders, resources, partners, books) are never deleted. Site settings
are only filled where they are blank; an existing value is always kept.

Restore modes write a JSON safety dump to ``settings.BACKUP_ROOT`` first.
All text comes from backend/seed/*.json; administrator accounts are never
deleted.
"""
import hashlib
import json
import os
from datetime import datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import User
from apps.catalogue.models import Book
from apps.content.models import (
    Career,
    DigitalPartner,
    News,
    Page,
    Resource,
    Section,
    SiteSetting,
    Tender,
)

SEED_DIR = Path(settings.BASE_DIR) / "seed"

NAVIGATION = [
    {
        "label": "Books",
        "href": "/books/",
        "panel": {
            "intro": "More than 1,000 titles for every stage of learning — from Grade 1 to tertiary, plus readers and literature.",
            "columns": [
                {
                    "title": "Curriculum",
                    "links": [
                        ["CBE books", "/books/?collection=CBE", "Grade 1–4 learner books"],
                        ["Secondary books", "/books/?collection=Secondary", "Form 1–4 course books"],
                        ["Revision & TopMark", "/books/?collection=Revision", "KCPE and KCSE revision"],
                    ],
                },
                {
                    "title": "Reading & reference",
                    "links": [
                        ["Readers & literature", "/books/?collection=Readers", "English and Kiswahili"],
                        ["Tertiary & reference", "/books/?collection=Tertiary", "College and career"],
                        ["Full catalogue", "/books/", "Search all titles"],
                    ],
                },
                {
                    "title": "Buying & support",
                    "links": [
                        ["Price lists", "/resources/#price-lists", "Current KLB prices"],
                        ["KLB ebookstore", "https://klbbooks.com/", "Buy digital editions"],
                        ["Bulk orders", "/contact/?type=bulk", "Schools and institutions"],
                    ],
                },
            ],
        },
    },
    {"label": "About", "href": "/about/"},
    {
        "label": "Services",
        "href": "/services/",
        "panel": {
            "intro": "A full publishing and printing house: editorial, design, translation, production and branded merchandise.",
            "columns": [
                {
                    "title": "Publishing",
                    "links": [
                        ["Publishing with KLB", "/services/#publishing", "Editorial and production"],
                        ["Design & editorial", "/services/#design", "Cover, interior and pre-press"],
                        ["Language translation", "/services/#translation", "Five languages and more"],
                    ],
                },
                {
                    "title": "Print & brand",
                    "links": [
                        ["Printing services", "/services/#printing", "Offset, digital and security print"],
                        ["Branding services", "/services/#branding", "Corporate merchandise"],
                    ],
                },
                {
                    "title": "Institution",
                    "links": [
                        ["Corporate social value", "/services/#csv", "Twachapisha Mwasoma"],
                        ["Service charter", "/about/#service-charter", "Our service commitment"],
                        ["Request a quote", "/contact/?type=quote", "Talk to our team"],
                    ],
                },
            ],
        },
    },
    {"label": "Digital", "href": "/digital/"},
    {"label": "News & media", "href": "/news/"},
    {"label": "Contact", "href": "/contact/"},
]

FOOTER_COLUMNS = [
    {
        "title": "Books",
        "links": [
            ["Full catalogue", "/books/"],
            ["CBE books", "/books/?collection=CBE"],
            ["Secondary books", "/books/?collection=Secondary"],
            ["Revision & TopMark", "/books/?collection=Revision"],
            ["Readers & literature", "/books/?collection=Readers"],
            ["Price lists", "/resources/#price-lists"],
        ],
    },
    {
        "title": "The Bureau",
        "links": [
            ["Our story", "/about/"],
            ["Mandate & governance", "/about/#mandate"],
            ["Leadership", "/about/#leadership"],
            ["Service charter", "/about/#service-charter"],
            ["Careers", "/careers/"],
            ["Tenders", "/tenders/"],
        ],
    },
    {
        "title": "Services",
        "links": [
            ["Publishing", "/services/#publishing"],
            ["Printing", "/services/#printing"],
            ["Branding", "/services/#branding"],
            ["Translation", "/services/#translation"],
            ["Design & editorial", "/services/#design"],
            ["Corporate social value", "/services/#csv"],
        ],
    },
]


def load_json(name):
    with open(SEED_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


SEED_FILES = ("cms-seed.json", "books.json")


def seed_fingerprint():
    """Return a short fingerprint of every seed file.

    The value changes only when the seed content itself changes. It marks which
    release has been recorded; it never triggers an overwrite of dashboard
    content in a deploy.
    """
    digest = hashlib.sha256()
    for name in SEED_FILES:
        path = SEED_DIR / name
        digest.update(name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:32]


def normalise_cover(value):
    if not value:
        return ""
    value = value.replace("assets/images/covers/", "/assets/covers/")
    if value.startswith("assets/"):
        value = "/" + value
    return value


class Command(BaseCommand):
    help = "Load the verified KLB pages, catalogue, news and settings into PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Restore the seed copy in place. Requires --confirm-reset. Never deletes rows.",
        )
        parser.add_argument(
            "--confirm-reset",
            action="store_true",
            help="Confirm that --reset may rewrite seed pages, sections and news.",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Create missing seed content. Never overwrites dashboard edits.",
        )
        parser.add_argument(
            "--force-refresh",
            action="store_true",
            help=(
                "Restore seed pages, sections and news in place. Dashboard-created "
                "rows and sections are kept."
            ),
        )
        parser.add_argument("--admin-email", default=os.getenv("SEED_ADMIN_EMAIL", "admin@klb.co.ke"))
        parser.add_argument("--admin-password", default=os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe-2026!"))

    def handle(self, *args, **options):
        reset = options["reset"]
        force = options["force_refresh"]
        if reset and not options["confirm_reset"]:
            raise CommandError(
                "--reset rewrites seed pages, sections and news in place. "
                "Nothing is deleted, but a JSON safety dump is written first. "
                "Re-run with --confirm-reset to continue."
            )
        if reset and (options["refresh"] or force):
            raise CommandError("Choose either --reset or --refresh/--force-refresh, not both.")

        restore = reset or force
        revision = seed_fingerprint()
        applied = SiteSetting.objects.filter(pk=1).values_list("seed_revision", flat=True).first() or ""
        refresh_due = bool(options["refresh"] and applied != revision)
        self._refresh = bool(refresh_due or restore)

        if restore:
            self._safety_dump()
            self.stdout.write(
                f"Restoring seed revision {revision} in place (no dashboard rows will be deleted)."
            )
        elif refresh_due:
            self.stdout.write(
                f"Seed revision {revision} is new; creating missing seed content only."
            )
        elif options["refresh"]:
            self.stdout.write("Seed revision already applied; keeping dashboard edits.")

        with transaction.atomic():
            settings_obj = self.seed_settings()
            pages = self.seed_pages(restore=restore)
            books = self.seed_books()
            news = self.seed_news(restore=restore)
            careers = self.seed_careers()
            tenders = self.seed_tenders()
            resources = self.seed_resources()
            digital_partners = self.seed_digital_partners()
            self.seed_admin(options["admin_email"], options["admin_password"])

            if self._refresh and settings_obj.seed_revision != revision:
                settings_obj.seed_revision = revision
                settings_obj.save(update_fields=["seed_revision"])

        self.stdout.write(self.style.SUCCESS("Seed complete:"))
        self.stdout.write(
            f"  settings: {settings_obj.site_name}\n"
            f"  pages: {pages}\n"
            f"  books: {books}\n"
            f"  news: {news}\n"
            f"  careers: {careers}\n"
            f"  tenders: {tenders}\n"
            f"  resources: {resources}\n"
            f"  digital partners: {digital_partners}"
        )

    # ------------------------------------------------------------------
    def _safety_dump(self):
        """Write a JSON dump before a restore mode changes any seed rows.

        The dump goes to ``settings.BACKUP_ROOT`` (never ``MEDIA_ROOT``) so it
        cannot be exposed as a public upload. A fresh database has nothing to
        protect, so the dump is skipped there.
        """
        if not (
            Page.objects.exists()
            or Section.objects.exists()
            or News.objects.exists()
            or SiteSetting.objects.exists()
            or Book.objects.exists()
        ):
            self.stdout.write("Fresh database; no safety dump needed.")
            return

        backup_root = Path(settings.BACKUP_ROOT)
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = backup_root / f"klb_preseed_{stamp}.json"
        counter = 2
        while path.exists():
            path = backup_root / f"klb_preseed_{stamp}_{counter}.json"
            counter += 1

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
            raise CommandError("Safety dump failed: dumpdata produced an empty file.")
        path.write_text(payload, encoding="utf-8")
        self.stdout.write(self.style.WARNING(f"Safety backup written to {path}"))

    # ------------------------------------------------------------------
    def seed_settings(self):
        defaults = {
            "site_name": "Kenya Literature Bureau PLC",
            "tagline": "Publishing & printing for you since 1947",
            "phone": "020 3541196/7",
            "phone_alt": "0711 318 188 · 0732 344 599",
            "address": "KLB Road, Bellevue Area, off Mombasa Road, P.O. Box 30022-00100, Nairobi",
            "contact_email": "info@klb.co.ke",
            "customer_email": "customer@klb.co.ke",
            "facebook": "https://www.facebook.com/klbkenya/",
            "twitter": "https://twitter.com/klb_kenya",
            "ebookstore": "https://klbbooks.com/",
            "footer_blurb": (
                "Kenya Literature Bureau PLC is a State corporation established in 1947 to publish, "
                "print and distribute educational, cultural and scientific materials for Kenya and the region."
            ),
            "seo_default_title": "Kenya Literature Bureau PLC | Books, publishing and printing since 1947",
            "seo_default_description": (
                "Kenya Literature Bureau PLC publishes and prints CBE, secondary, revision and readers titles. "
                "Search KLB books, buy e-books, and enquire about bulk orders or printing services."
            ),
            "og_image": "/assets/og-klb.jpg",
            "navigation": NAVIGATION,
            "footer_columns": FOOTER_COLUMNS,
            "statistics": [
                {"value": "1947", "label": "Established as the East African Literature Bureau", "animate": True},
                {"value": "1000", "suffix": "+", "label": "Titles published across every level", "animate": True},
                {"value": "250", "suffix": "+", "label": "E-books available worldwide", "animate": True},
                {"value": "300", "suffix": "+", "label": "Employees countrywide", "animate": True},
            ],
        }
        obj, created = SiteSetting.objects.get_or_create(pk=1, defaults=defaults)
        if created:
            self.stdout.write("Created site settings.")
            return obj

        # Existing settings belong to the dashboard. Fill only values that are
        # still blank so new seed fields can appear without replacing any value
        # an editor has saved.
        filled = []
        for field, value in defaults.items():
            current = getattr(obj, field)
            if field in ("navigation", "footer_columns", "statistics"):
                is_blank = not current
            else:
                is_blank = current is None or current == ""
            if is_blank:
                setattr(obj, field, value)
                filled.append(field)
        if filled:
            obj.save(update_fields=filled)
            self.stdout.write(f"Filled blank site settings: {', '.join(filled)}")
        return obj

    def seed_pages(self, restore=False):
        data = load_json("cms-seed.json")
        count = 0
        for index, page_data in enumerate(data["pages"]):
            defaults = {
                "title": page_data["title"],
                "meta_title": page_data.get("metaTitle", ""),
                "meta_description": page_data.get("metaDescription", ""),
                "template": page_data.get("template", "page"),
                "status": page_data.get("status", "published"),
                "sort_order": index,
            }
            page, created = Page.objects.get_or_create(slug=page_data["slug"], defaults=defaults)
            if created:
                count += 1
            elif restore:
                changed = False
                for field, value in defaults.items():
                    if getattr(page, field) != value:
                        setattr(page, field, value)
                        changed = True
                if changed:
                    page.save()
                    count += 1
            self._seed_page_sections(page, page_data.get("sections", []), restore=restore)
        return count

    def _seed_page_sections(self, page, sections, restore=False):
        """Create missing seed sections and (only when restoring) refresh them.

        A section is seed-origin when its ``seed_key`` matches the seed label.
        Sections created by older releases have no ``seed_key`` yet, so a
        section whose label appears in the seed file is adopted. Dashboard
        sections have a different label or stay blank-keyed and are never
        updated or deleted.
        """
        for section_index, section_data in enumerate(sections):
            label = section_data.get("label", "Section")
            seed_key = (slugify(label) or "section")[:100]
            existing = page.sections.filter(seed_key=seed_key).first()
            if existing is None:
                existing = page.sections.filter(seed_key="", label=label).first()
                if existing is not None:
                    existing.seed_key = seed_key
                    existing.save(update_fields=["seed_key"])

            values = {
                "label": label,
                "kind": section_data.get("kind", "html"),
                "html": section_data.get("html", ""),
                "settings": section_data.get("settings") or {},
                "sort_order": section_index,
            }
            if existing is None:
                Section.objects.create(page=page, seed_key=seed_key, **values)
            elif restore:
                changed = False
                for field, value in values.items():
                    if getattr(existing, field) != value:
                        setattr(existing, field, value)
                        changed = True
                if changed:
                    existing.save()


    def seed_books(self):
        data = load_json("books.json")
        count = 0
        for index, item in enumerate(data):
            defaults = {
                "title": item.get("title", ""),
                "category": item.get("category", ""),
                "categories": item.get("categories") or [],
                "collection": item.get("collection", ""),
                "level": item.get("level", ""),
                "language": item.get("language", ""),
                "subject": item.get("subject", ""),
                "price": Decimal(str(item["price"])) if item.get("price") is not None else None,
                "currency": item.get("currency", "KES"),
                "isbn": item.get("isbn") or "",
                "publisher": item.get("publisher") or "Kenya Literature Bureau PLC",
                "cover": normalise_cover(item.get("cover", "")),
                "description": item.get("description", ""),
                "store_url": item.get("storeUrl") or "",
                "source_url": item.get("sourceUrl") or "",
                "featured": bool(item.get("featured")),
                "new_arrival": bool(item.get("newArrival")),
                "sort_order": index,
            }
            _, created = Book.objects.get_or_create(slug=item["slug"], defaults=defaults)
            if created:
                count += 1
        return count

    def seed_news(self, restore=False):
        data = load_json("cms-seed.json")
        count = 0
        for item in data["news"]:
            slug = item.get("slug") or slugify(item["title"])[:240]
            values = {
                "title": item["title"],
                "category": item.get("category", ""),
                "summary": item.get("summary", ""),
                "body_html": item.get("bodyHtml", ""),
                "published_at": item["publishedAt"],
                "featured": bool(item.get("featured")),
            }
            article, created = News.objects.get_or_create(slug=slug, defaults=values)
            if created:
                count += 1
            elif restore:
                changed = False
                for field, value in values.items():
                    if getattr(article, field) != value:
                        setattr(article, field, value)
                        changed = True
                if changed:
                    article.save()
                    count += 1
        return count

    def seed_careers(self):
        data = load_json("cms-seed.json")
        count = 0
        for item in data["careers"]:
            _, created = Career.objects.get_or_create(
                title=item["title"],
                defaults={
                    "department": item.get("department", ""),
                    "location": item.get("location", ""),
                    "employment_type": item.get("employmentType", ""),
                    "summary": item.get("summary", ""),
                    "body_html": item.get("bodyHtml", ""),
                    "apply_url": item.get("applyUrl", ""),
                },
            )
            if created:
                count += 1
        return count

    def seed_tenders(self):
        data = load_json("cms-seed.json")
        count = 0
        for index, item in enumerate(data["tenders"]):
            tender, created = Tender.objects.get_or_create(
                title=item["title"],
                defaults={
                    "category": item.get("category", ""),
                    "summary": item.get("summary", ""),
                    "body_html": item.get("bodyHtml", ""),
                    "document_url": item.get("documentUrl", ""),
                    "published_on": item.get("publishedOn"),
                    "is_open": item.get("isOpen", True),
                    "sort_order": index,
                },
            )
            if created:
                count += 1
            elif "\\" in (tender.document_url or ""):
                tender.document_url = item.get("documentUrl", tender.document_url)
                tender.save(update_fields=["document_url"])
        return count

    def seed_resources(self):
        data = load_json("cms-seed.json")
        count = 0
        for item in data["resources"]:
            resource, created = Resource.objects.get_or_create(
                title=item["title"],
                defaults={
                    "category": item["category"],
                    "description": item.get("description", ""),
                    "file_url": item.get("fileUrl", ""),
                    "external": bool(item.get("external")),
                    "sort_order": item.get("sortOrder", 0),
                },
            )
            if created:
                count += 1
            elif "\\" in (resource.file_url or ""):
                # Repair values saved by older seeds that used Windows-style
                # backslashes; these resolve to the wrong page on the site.
                resource.file_url = item.get("fileUrl", resource.file_url)
                resource.save(update_fields=["file_url"])
        return count

    def seed_digital_partners(self):
        data = load_json("cms-seed.json")
        count = 0
        for item in data.get("digital_partners", []):
            _, created = DigitalPartner.objects.get_or_create(
                key=item["key"],
                defaults={
                    "name": item["name"],
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "sort_order": item.get("sortOrder", 0),
                    "is_active": True,
                },
            )
            if created:
                count += 1
        return count

    def seed_admin(self, email, password):
        email = email.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f"Administrator {email} already exists.")
            return
        username = email.split("@")[0][:150] or "admin"
        base_username = username
        counter = 2
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user = User(
            username=username,
            email=email,
            full_name="KLB Administrator",
            role=User.Role.ADMINISTRATOR,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.WARNING(f"Created administrator {email} (change the password after first sign-in)."))
