from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils.text import slugify


class Book(models.Model):
    """A catalogue title. Prices are indicative and editable in the dashboard."""

    slug = models.SlugField(max_length=180, unique=True)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True)
    categories = models.JSONField(default=list, blank=True)
    collection = models.CharField(max_length=80, blank=True)
    level = models.CharField(max_length=80, blank=True)
    language = models.CharField(max_length=120, blank=True)
    subject = models.CharField(max_length=160, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="KES")
    isbn = models.CharField(max_length=32, blank=True)
    publisher = models.CharField(max_length=160, default="Kenya Literature Bureau PLC")
    cover = models.CharField(
        max_length=300,
        blank=True,
        help_text="Public path or absolute URL, e.g. /assets/covers/example.webp",
    )
    cover_upload = models.FileField(
        upload_to="covers/",
        blank=True,
        help_text="Optional upload. Takes precedence over the cover path.",
    )
    description = models.TextField(blank=True)
    search_vector = SearchVectorField(null=True, blank=True)
    store_url = models.URLField(max_length=500, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    featured = models.BooleanField(default=False)
    new_arrival = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-featured", "sort_order", "title"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["collection"]),
            models.Index(fields=["level"]),
            models.Index(fields=["is_published"]),
            GinIndex(fields=["search_vector"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:180]
        super().save(*args, **kwargs)
        # Update search vector for full-text search
        if self.search_vector is None:
            from django.contrib.postgres.search import SearchVector
            Book.objects.filter(pk=self.pk).update(
                search_vector=SearchVector("title", weight="A")
                + SearchVector("subject", weight="B")
                + SearchVector("category", weight="B")
                + SearchVector("description", weight="C")
            )

    @property
    def cover_url(self) -> str:
        if self.cover_upload:
            return self.cover_upload.url
        return self.cover or "/assets/klb-logo-blue.png"

    def __str__(self) -> str:
        return self.title
