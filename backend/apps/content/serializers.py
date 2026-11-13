from django.utils.text import slugify
from rest_framework import serializers

from .models import BackupRecord, Career, DigitalPartner, DropdownOption, News, Page, Resource, Section, SiteSetting, TeamPhoto, Tender, WebsiteTheme


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "label", "kind", "html", "settings", "sort_order"]
        read_only_fields = ["id"]

    def validate_settings(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Section settings must be a JSON object.")
        return value


class PageListSerializer(serializers.ModelSerializer):
    section_count = serializers.IntegerField(source="sections.count", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id", "slug", "title", "meta_title", "meta_description",
            "template", "status", "sort_order", "section_count", "updated_at",
        ]


class PageDetailSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True)

    class Meta:
        model = Page
        fields = [
            "id", "slug", "title", "meta_title", "meta_description",
            "template", "status", "sort_order", "updated_at", "sections",
        ]
        read_only_fields = ["id", "updated_at"]

    def _is_super(self):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.is_super_administrator)

    def _write_sections(self, page, sections):
        page.sections.all().delete()
        for index, section in enumerate(sections):
            Section.objects.create(
                page=page,
                label=section.get("label", "Section"),
                kind=section.get("kind", Section.Kind.HTML),
                html=section.get("html", ""),
                settings=section.get("settings") or {},
                sort_order=section.get("sort_order", index),
            )

    def create(self, validated_data):
        sections = validated_data.pop("sections", [])
        if not self._is_super():
            validated_data["template"] = Page.Template.PAGE
            sections = [
                {
                    **section,
                    "kind": Section.Kind.HTML,
                    "settings": {},
                }
                for section in sections
            ]
        page = Page.objects.create(**validated_data)
        self._write_sections(page, sections)
        return page

    def update(self, instance, validated_data):
        sections = validated_data.pop("sections", None)
        if not self._is_super():
            # Editors work on content, not on source-level structure or JSON.
            # Match by id so reordering or removing a section cannot attach
            # another section's kind or settings to it.
            validated_data.pop("template", None)
            if sections is not None:
                existing = {section.pk: section for section in instance.sections.all()}
                raw_sections = self.initial_data.get("sections") or []
                prepared = []
                for index, section in enumerate(sections):
                    raw = raw_sections[index] if index < len(raw_sections) else {}
                    try:
                        section_id = int(raw.get("id"))
                    except (TypeError, ValueError):
                        section_id = None
                    previous = existing.get(section_id)
                    prepared.append(
                        {
                            **section,
                            "kind": previous.kind if previous else Section.Kind.HTML,
                            "settings": previous.settings if previous else {},
                        }
                    )
                sections = prepared
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if sections is not None:
            self._write_sections(instance, sections)
        return instance


class NewsSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True, max_length=255)

    class Meta:
        model = News
        fields = [
            "id", "title", "slug", "category", "summary", "body_html", "image",
            "published_at", "featured", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _unique_slug(self, title):
        base = slugify(title)[:220] or "news"
        candidate = base
        counter = 2
        qs = News.objects.all()
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        while qs.filter(slug=candidate).exists():
            candidate = f"{base[:210]}-{counter}"
            counter += 1
        return candidate

    def validate_slug(self, value):
        value = (value or "").strip()
        if not value:
            return value
        qs = News.objects.filter(slug=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Another news item already uses this URL slug.")
        return value

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = self._unique_slug(validated_data.get("title", ""))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "slug" in validated_data and not validated_data.get("slug"):
            validated_data["slug"] = self._unique_slug(
                validated_data.get("title", instance.title)
            )
        return super().update(instance, validated_data)


class CareerSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Career
        fields = [
            "id", "title", "department", "location", "employment_type", "summary",
            "body_html", "apply_url", "opening_date", "closing_date", "status", "is_open", "sort_order",
        ]


class TenderSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Tender
        fields = [
            "id", "title", "category", "summary", "body_html", "document_url",
            "published_on", "opening_date", "closing_date", "status", "is_open", "sort_order",
        ]


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ["id", "title", "category", "description", "file_url", "external", "sort_order"]


class TeamPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamPhoto
        fields = ["key", "name", "role", "photo", "updated_at"]
        read_only_fields = ["updated_at"]


class DigitalPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalPartner
        fields = ["id", "key", "name", "url", "logo", "description", "sort_order", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class BackupRecordSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True, default="")
    restored_by_name = serializers.CharField(source="restored_by.display_name", read_only=True, default="")
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BackupRecord
        fields = [
            "id", "filename", "backup_type", "size", "components", "status",
            "status_label", "error", "storage", "created_by", "created_by_name",
            "created_at", "restored_at", "restored_by", "restored_by_name",
        ]
        read_only_fields = fields


class WebsiteThemeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    # The form allows the slug to be left blank; the model generates one from
    # the theme name in save(). Keep it optional here so validation passes.
    slug = serializers.SlugField(required=False, allow_blank=True)

    def validate_slug(self, value):
        value = (value or "").strip()
        if not value:
            # The model generates a slug from the name when this is blank.
            return value
        queryset = WebsiteTheme.objects.filter(slug=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "A theme with this slug already exists. Choose a different slug "
                "or leave it blank."
            )
        return value

    class Meta:
        model = WebsiteTheme
        fields = ["id", "name", "slug", "description", "css_class", "start_date", "end_date", "is_active", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = [
            "site_name", "tagline", "phone", "phone_alt", "address",
            "contact_email", "customer_email", "facebook", "twitter", "instagram",
            "linkedin", "ebookstore", "announcement", "footer_blurb",
            "seo_default_title", "seo_default_description", "og_image",
            "maintenance_mode", "maintenance_message", "backup_retention",
            "navigation", "footer_columns", "statistics", "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def validate_navigation(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Navigation must be a list of items.")
        return value

    def validate_footer_columns(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Footer columns must be a list of items.")
        return value


class DropdownOptionSerializer(serializers.ModelSerializer):
    group_label = serializers.CharField(source="get_group_display", read_only=True)

    class Meta:
        model = DropdownOption
        fields = ["id", "group", "group_label", "value", "label", "sort_order", "is_active"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "value": {"required": False, "allow_blank": True},
        }

    def validate_value(self, value):
        return (value or "").strip()

    def validate_label(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Enter a label.")
        return value

    def validate(self, attrs):
        group = attrs.get("group", getattr(self.instance, "group", ""))
        value = attrs.get("value", getattr(self.instance, "value", ""))
        label = attrs.get("label", getattr(self.instance, "label", ""))
        # A blank value is generated from the label, matching the model's
        # save() behaviour, so the uniqueness check can run against it.
        if not value:
            value = slugify(label)[:120]
            attrs["value"] = value
        qs = DropdownOption.objects.filter(group=group, value__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if value and qs.exists():
            raise serializers.ValidationError({"value": "That option already exists in this group."})
        return attrs
