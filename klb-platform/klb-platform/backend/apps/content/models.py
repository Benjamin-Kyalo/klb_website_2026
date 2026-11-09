from django.db import models

from .sanitize import clean_html


class Page(models.Model):
    class Template(models.TextChoices):
        PAGE = "page", "Standard page"
        CATALOGUE = "catalogue", "Catalogue page"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=200)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    template = models.CharField(max_length=20, choices=Template.choices, default=Template.PAGE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    sort_order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:
        return self.title


class Section(models.Model):
    class Kind(models.TextChoices):
        HTML = "html", "Rich HTML block"
        BOOK_GRID = "book_grid", "Book grid"
        NEWS_LIST = "news_list", "News list"
        CAREERS_LIST = "careers_list", "Careers list"
        TENDERS_LIST = "tenders_list", "Tenders list"
        RESOURCES_LIST = "resources_list", "Resources list"

    page = models.ForeignKey(Page, related_name="sections", on_delete=models.CASCADE)
    label = models.CharField(max_length=160)
    kind = models.CharField(max_length=30, choices=Kind.choices, default=Kind.HTML)
    html = models.TextField(blank=True)
    settings = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        # Sanitise rich HTML on every save so stored content is safe to render.
        if self.kind == self.Kind.HTML:
            self.html = clean_html(self.html)
        if isinstance(self.settings, dict) and self.settings.get("introHtml"):
            self.settings = {**self.settings, "introHtml": clean_html(self.settings["introHtml"])}
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.page.slug} / {self.label}"


class News(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=80, blank=True)
    summary = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    image = models.CharField(max_length=300, blank=True)
    published_at = models.DateField()
    featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name_plural = "news"

    def save(self, *args, **kwargs):
        self.body_html = clean_html(self.body_html)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class Career(models.Model):
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    employment_type = models.CharField(max_length=80, blank=True)
    summary = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    apply_url = models.URLField(max_length=500, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    is_open = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_open", "sort_order", "-id"]

    def save(self, *args, **kwargs):
        self.body_html = clean_html(self.body_html)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class Tender(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True)
    summary = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    document_url = models.CharField(max_length=500, blank=True)
    published_on = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    is_open = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = [models.F("published_on").desc(nulls_last=True), "-id"]

    def save(self, *args, **kwargs):
        self.body_html = clean_html(self.body_html)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class Resource(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    file_url = models.CharField(max_length=500)
    external = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:
        return self.title


class DropdownOption(models.Model):
    """A configurable choice used by dashboard forms.

    Storing these in the database keeps classification lists consistent and
    lets administrators add a new category without a code change.
    """

    class Group(models.TextChoices):
        NEWS_CATEGORY = "news_category", "News category"
        PUBLICATION_CATEGORY = "publication_category", "Catalogue category"
        COLLECTION = "collection", "Catalogue collection"
        DEPARTMENT = "department", "Department"
        JOB_LOCATION = "job_location", "Job location"
        EMPLOYMENT_TYPE = "employment_type", "Employment type"
        TENDER_CATEGORY = "tender_category", "Tender category"
        RESOURCE_CATEGORY = "resource_category", "Resource category"
        EVENT_CATEGORY = "event_category", "Event category"

    group = models.CharField(max_length=40, choices=Group.choices)
    value = models.CharField(max_length=120)
    label = models.CharField(max_length=160)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group", "sort_order", "label"]
        constraints = [
            models.UniqueConstraint(fields=["group", "value"], name="unique_dropdown_option"),
        ]
        verbose_name = "dropdown option"
        verbose_name_plural = "dropdown options"

    def save(self, *args, **kwargs):
        if not self.value:
            from django.utils.text import slugify

            self.value = slugify(self.label)[:120]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_group_display()}: {self.label}"


class SiteSetting(models.Model):
    """Single row of editable global settings (pk=1)."""

    site_name = models.CharField(max_length=160, default="Kenya Literature Bureau")
    tagline = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    phone_alt = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    customer_email = models.EmailField(blank=True)
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    ebookstore = models.URLField(blank=True)
    announcement = models.CharField(max_length=300, blank=True)
    footer_blurb = models.TextField(blank=True)
    seo_default_title = models.CharField(max_length=200, blank=True)
    seo_default_description = models.TextField(blank=True)
    og_image = models.CharField(max_length=300, blank=True)
    navigation = models.JSONField(default=list, blank=True)
    footer_columns = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    @classmethod
    def load(cls) -> "SiteSetting":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.site_name
