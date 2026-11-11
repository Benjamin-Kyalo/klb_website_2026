"""Seed the KLB website with verified content.

Usage:
    python manage.py seed_content             # create anything that is missing
    python manage.py seed_content --reset     # replace pages, catalogue and settings

The command is safe to run more than once. It never deletes administrator
accounts. All text comes from backend/seed/*.json.
"""
import json
import os
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
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
                        ["CBC books", "/books/?collection=CBC", "Grade 1–4 learner books"],
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
            ["CBC books", "/books/?collection=CBC"],
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
        parser.add_argument("--reset", action="store_true", help="Delete existing content before seeding.")
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Update existing pages, sections and news copy from the seed files.",
        )
        parser.add_argument("--admin-email", default=os.getenv("SEED_ADMIN_EMAIL", "admin@klb.co.ke"))
        parser.add_argument("--admin-password", default=os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe-2026!"))

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Resetting content tables...")
            Section.objects.all().delete()
            Page.objects.all().delete()
            Book.objects.all().delete()
            News.objects.all().delete()
            Career.objects.all().delete()
            Tender.objects.all().delete()
            Resource.objects.all().delete()
            SiteSetting.objects.all().delete()

        settings_obj = self.seed_settings()
        pages = self.seed_pages(options["refresh"])
        books = self.seed_books()
        news = self.seed_news(options["refresh"])
        careers = self.seed_careers()
        tenders = self.seed_tenders()
        resources = self.seed_resources()
        digital_partners = self.seed_digital_partners()
        self.seed_admin(options["admin_email"], options["admin_password"])

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
                "Kenya Literature Bureau PLC publishes and prints CBC, secondary, revision and readers titles. "
                "Search KLB books, buy e-books, and enquire about bulk orders or printing services."
            ),
            "og_image": "/assets/og-klb.jpg",
            "navigation": NAVIGATION,
            "footer_columns": FOOTER_COLUMNS,
            "statistics": [
                {"value": "1947", "label": "Established as the East African Literature Bureau", "animate": False},
                {"value": "1000", "suffix": "+", "label": "Titles published across every level", "animate": True},
                {"value": "250", "suffix": "+", "label": "E-books available worldwide", "animate": True},
                {"value": "300", "suffix": "+", "label": "Employees countrywide", "animate": True},
            ],
        }
        obj, created = SiteSetting.objects.get_or_create(pk=1, defaults=defaults)
        if created:
            self.stdout.write("Created site settings.")
        return obj

    def seed_pages(self, refresh=False):
        data = load_json("cms-seed.json")
        count = 0
        for index, page_data in enumerate(data["pages"]):
            page, created = Page.objects.get_or_create(
                slug=page_data["slug"],
                defaults={
                    "title": page_data["title"],
                    "meta_title": page_data.get("metaTitle", ""),
                    "meta_description": page_data.get("metaDescription", ""),
                    "template": page_data.get("template", "page"),
                    "status": page_data.get("status", "published"),
                    "sort_order": index,
                },
            )
            if created or refresh:
                if not created:
                    page.title = page_data["title"]
                    page.meta_title = page_data.get("metaTitle", "")
                    page.meta_description = page_data.get("metaDescription", "")
                    page.template = page_data.get("template", "page")
                    page.sort_order = index
                    page.save()
                    page.sections.all().delete()
                for section_index, section_data in enumerate(page_data.get("sections", [])):
                    Section.objects.create(
                        page=page,
                        label=section_data.get("label", "Section"),
                        kind=section_data.get("kind", "html"),
                        html=section_data.get("html", ""),
                        settings=section_data.get("settings") or {},
                        sort_order=section_index,
                    )
                count += 1
        return count

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

    def seed_news(self, refresh=False):
        data = load_json("cms-seed.json")
        count = 0
        for item in data["news"]:
            slug = item.get("slug") or slugify(item["title"])[:240]
            article, created = News.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": item["title"],
                    "category": item.get("category", ""),
                    "summary": item.get("summary", ""),
                    "body_html": item.get("bodyHtml", ""),
                    "published_at": item["publishedAt"],
                    "featured": bool(item.get("featured")),
                },
            )
            if created:
                count += 1
            elif refresh:
                article.title = item["title"]
                article.category = item.get("category", "")
                article.summary = item.get("summary", "")
                article.body_html = item.get("bodyHtml", "")
                article.published_at = item["publishedAt"]
                article.featured = bool(item.get("featured"))
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
            _, created = Tender.objects.get_or_create(
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
        return count

    def seed_resources(self):
        data = load_json("cms-seed.json")
        count = 0
        for item in data["resources"]:
            _, created = Resource.objects.get_or_create(
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
