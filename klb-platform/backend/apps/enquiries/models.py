from django.db import models


class Enquiry(models.Model):
    class Type(models.TextChoices):
        GENERAL = "general", "General enquiry"
        BULK = "bulk", "Bulk order"
        ORDER = "order", "Order or delivery question"
        QUOTE = "quote", "Printing or design quote"
        PUBLISHING = "publishing", "Publishing a manuscript"
        TRANSLATION = "translation", "Translation services"
        PRINTING = "printing", "Printing services"
        BRANDING = "branding", "Branding services"
        DIGITAL = "digital", "Digital editions"
        MEDIA = "media", "Media enquiry"
        EVENTS = "events", "Events and school visits"
        PROCUREMENT = "procurement", "Tender or procurement"
        ACCESS = "access", "Access to information"
        COMPLAINTS = "complaints", "Complaint or feedback"
        CAREERS = "careers", "Recruitment"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=60, blank=True)
    organisation = models.CharField(max_length=180, blank=True)
    enquiry_type = models.CharField(max_length=30, choices=Type.choices, default=Type.GENERAL)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    internal_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "enquiries"

    def __str__(self) -> str:
        return f"{self.name} - {self.subject}"


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email
