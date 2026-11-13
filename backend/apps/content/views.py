import os
import re
import json
import zipfile

from django.conf import settings
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from pathlib import Path
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.activity import log_activity
from apps.accounts.models import ActivityLog
from apps.accounts.permissions import IsStaff, ModulePermission
from apps.accounts.rbac import has_permission, require_permission
from apps.catalogue.models import Book
from apps.catalogue.serializers import BookSerializer
from apps.enquiries.models import Enquiry, Subscriber
from apps.enquiries.serializers import EnquirySerializer, SubscriberSerializer

from .models import BackupRecord, Career, DigitalPartner, DropdownOption, News, Page, Resource, SiteSetting, TeamPhoto, Tender, WebsiteTheme
from .serializers import (
    BackupRecordSerializer,
    CareerSerializer,
    DigitalPartnerSerializer,
    DropdownOptionSerializer,
    NewsSerializer,
    PageDetailSerializer,
    PageListSerializer,
    ResourceSerializer,
    SiteSettingSerializer,
    TeamPhotoSerializer,
    TenderSerializer,
    WebsiteThemeSerializer,
)
from .team_photos import inject_team_photos, team_members_from_html


# ---------------------------------------------------------------------------
# Public site endpoints
# ---------------------------------------------------------------------------
class SiteView(APIView):
    """Global settings, navigation and a lightweight page index."""

    def get(self, request):
        settings_obj = SiteSetting.load()
        pages = Page.objects.filter(status=Page.Status.PUBLISHED).values("slug", "title", "template")
        return Response(
            {
                "settings": SiteSettingSerializer(settings_obj).data,
                "navigation": settings_obj.navigation or [],
                "pages": list(pages),
            }
        )


class PageDetailView(APIView):
    def get(self, request, slug):
        page = get_object_or_404(Page, slug=slug, status=Page.Status.PUBLISHED)
        data = PageDetailSerializer(page).data
        photos = dict(TeamPhoto.objects.exclude(photo="").values_list("key", "photo"))
        if photos:
            for section in data.get("sections", []):
                html = section.get("html") or ""
                if "team-card" in html or "leadership-grid" in html:
                    section["html"] = inject_team_photos(html, photos)
        return Response(data)


class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NewsSerializer
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        qs = News.objects.filter(status=News.Status.PUBLISHED)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__iexact=category)
        if self.request.query_params.get("featured") in {"1", "true"}:
            qs = qs.filter(featured=True)
        search = self.request.query_params.get("q")
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(summary__icontains=search)
        limit = self.request.query_params.get("limit")
        if limit and limit.isdigit():
            qs = qs[: int(limit)]
        return qs


class CareersView(APIView):
    def get(self, request):
        qs = Career.objects.all()
        if request.query_params.get("all") not in {"1", "true"}:
            qs = qs.filter(is_open=True)
        return Response(CareerSerializer(qs, many=True).data)


class TendersView(APIView):
    def get(self, request):
        qs = Tender.objects.all()
        if request.query_params.get("all") not in {"1", "true"}:
            qs = qs.filter(is_open=True)
        return Response(TenderSerializer(qs, many=True).data)


class ResourcesView(APIView):
    def get(self, request):
        qs = Resource.objects.all()
        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return Response(ResourceSerializer(qs, many=True).data)


class DigitalPartnersView(APIView):
    def get(self, request):
        qs = DigitalPartner.objects.filter(is_active=True).order_by("sort_order", "name")
        return Response(DigitalPartnerSerializer(qs, many=True).data)


class ActiveThemeView(APIView):
    def get(self, request):
        from django.utils import timezone
        today = timezone.now().date()
        theme = WebsiteTheme.objects.filter(
            is_active=True, start_date__lte=today, end_date__gte=today,
        ).order_by("-start_date").first()
        if theme:
            return Response(WebsiteThemeSerializer(theme).data)
        return Response({"active": False})


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------
class AdminActivityMixin:
    """Log create, update, delete and publication changes in one place."""

    permission_module = None
    publish_field = None
    published_value = True
    unpublished_value = False

    def _is_published(self, instance):
        if not self.publish_field:
            return None
        return getattr(instance, self.publish_field) == self.published_value

    def _label(self, obj):
        return getattr(obj, "title", "") or str(obj)

    def _log(self, action, obj, detail=""):
        log_activity(self.request, action, self.permission_module, obj, self._label(obj), detail)

    def perform_create(self, serializer):
        if self.publish_field and not has_permission(
            self.request.user, self.permission_module, "publish"
        ):
            serializer.validated_data[self.publish_field] = self.unpublished_value
        obj = serializer.save()
        self._log(ActivityLog.Action.CREATE, obj, "Record created.")
        if self.publish_field and self._is_published(obj):
            self._log(ActivityLog.Action.PUBLISH, obj, "Created as published.")

    def perform_update(self, serializer):
        instance = serializer.instance
        before_published = self._is_published(instance)
        data = serializer.validated_data

        if self.publish_field and self.publish_field in data:
            requested_published = data[self.publish_field] == self.published_value
            if requested_published != before_published and not has_permission(
                self.request.user, self.permission_module, "publish"
            ):
                # Silently keep the old state; the response still carries the
                # truthful value so the UI can explain the restriction.
                data[self.publish_field] = getattr(instance, self.publish_field)

        obj = serializer.save()
        changed = ", ".join(sorted(serializer.validated_data.keys()))
        if "sections" in changed:
            changed = changed.replace("sections", "page sections")
        self._log(ActivityLog.Action.UPDATE, obj, f"Updated: {changed}." if changed else "Record updated.")

        after_published = self._is_published(obj)
        if self.publish_field and before_published != after_published:
            action = ActivityLog.Action.PUBLISH if after_published else ActivityLog.Action.UNPUBLISH
            self._log(action, obj, "Publication status changed.")

    def perform_destroy(self, instance):
        label = self._label(instance)
        log_activity(
            self.request,
            ActivityLog.Action.DELETE,
            self.permission_module,
            instance,
            label,
            "Record deleted.",
        )
        instance.delete()


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
class AdminStatsView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        user = request.user
        data = {}

        def add(module, key, value):
            data[key] = value if has_permission(user, module, "view") else None

        add("pages", "pages", Page.objects.count())
        add(
            "pages",
            "published_pages",
            Page.objects.filter(status=Page.Status.PUBLISHED).count(),
        )
        add("books", "books", Book.objects.count())
        add(
            "books",
            "published_books",
            Book.objects.filter(is_published=True).count(),
        )
        add("news", "news", News.objects.count())
        add("careers", "careers", Career.objects.count())
        add("tenders", "tenders", Tender.objects.count())
        add("resources", "resources", Resource.objects.count())
        add(
            "enquiries",
            "new_enquiries",
            Enquiry.objects.filter(status=Enquiry.Status.NEW).count(),
        )
        add("enquiries", "enquiries", Enquiry.objects.count())
        add(
            "subscribers",
            "subscribers",
            Subscriber.objects.filter(is_active=True).count(),
        )
        return Response(data)


class AdminPageViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "pages"
    publish_field = "status"
    published_value = Page.Status.PUBLISHED
    unpublished_value = Page.Status.DRAFT
    queryset = Page.objects.all().prefetch_related("sections")
    serializer_class = PageDetailSerializer
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "slug"]

    def get_serializer_class(self):
        if self.action == "list":
            return PageListSerializer
        return PageDetailSerializer

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, slug=None):
        require_permission(request.user, "pages", "view")
        page = self.get_object()
        new_slug = f"{page.slug}-copy"
        counter = 2
        while Page.objects.filter(slug=new_slug).exists():
            new_slug = f"{page.slug}-copy-{counter}"
            counter += 1
        copy = Page.objects.create(
            slug=new_slug,
            title=f"{page.title} (copy)",
            meta_title=page.meta_title,
            meta_description=page.meta_description,
            template=page.template,
            status=Page.Status.DRAFT,
            sort_order=page.sort_order + 1,
        )
        for section in page.sections.all():
            section.pk = None
            section.page = copy
            section.save()
        log_activity(request, ActivityLog.Action.CREATE, "pages", copy, copy.title, "Duplicated page.")
        return Response(PageDetailSerializer(copy, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AdminTeamPhotoView(APIView):
    """List and update photos for the About-page leadership cards."""

    permission_classes = [ModulePermission]
    permission_module = "pages"

    def _leadership(self):
        page = Page.objects.filter(slug="about").prefetch_related("sections").first()
        if not page:
            return None, None
        for section in page.sections.all():
            html = section.html or ""
            if "team-card" in html or "leadership-grid" in html:
                return page, section
        return page, None

    def _members(self):
        page, section = self._leadership()
        members = team_members_from_html(section.html) if section else []
        saved = {row.key: row for row in TeamPhoto.objects.all()}
        rows = []
        for member in members:
            row = saved.get(member["key"])
            rows.append(
                {
                    **member,
                    "photo": row.photo if row else "",
                    "updated_at": row.updated_at.isoformat() if row else None,
                }
            )
        return page, section, rows

    def get(self, request):
        page, section, members = self._members()
        return Response(
            {
                "page_slug": page.slug if page else None,
                "section_found": bool(section),
                "members": members,
            }
        )

    def patch(self, request, key):
        _page, _section, members = self._members()
        member = next((item for item in members if item["key"] == key), None)
        if member is None:
            return Response(
                {"detail": "That team card was not found on the About page."},
                status=status.HTTP_404_NOT_FOUND,
            )

        photo = (request.data.get("photo") or "").strip()
        if photo and not (
            photo.startswith("/media/")
            or photo.startswith("http://")
            or photo.startswith("https://")
        ):
            return Response(
                {"detail": "Choose an uploaded image for the team photo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        row, _created = TeamPhoto.objects.update_or_create(
            key=key,
            defaults={"name": member["name"], "role": member["role"], "photo": photo},
        )
        log_activity(
            request,
            ActivityLog.Action.UPDATE,
            "pages",
            row,
            member["name"] or key,
            "Team photo updated." if photo else "Team photo removed.",
        )
        return Response(TeamPhotoSerializer(row).data)


class AdminBookViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "books"
    publish_field = "is_published"
    published_value = True
    unpublished_value = False
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "isbn", "category", "subject", "collection"]
    ordering_fields = ["title", "price", "created_at", "sort_order"]


class AdminNewsViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "news"
    publish_field = "status"
    published_value = News.Status.PUBLISHED
    unpublished_value = News.Status.DRAFT
    queryset = News.objects.all()
    serializer_class = NewsSerializer
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "summary", "category"]
    ordering_fields = ["published_at", "title"]


class AdminCareerViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "careers"
    publish_field = "is_open"
    published_value = True
    unpublished_value = False
    queryset = Career.objects.all()
    serializer_class = CareerSerializer


class AdminTenderViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "tenders"
    publish_field = "is_open"
    published_value = True
    unpublished_value = False
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer


class AdminResourceViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "resources"
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer


class AdminDigitalPartnerViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "pages"
    queryset = DigitalPartner.objects.all().order_by("sort_order", "name")
    serializer_class = DigitalPartnerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["sort_order", "name", "is_active"]

    def perform_create(self, serializer):
        obj = serializer.save()
        self._log(ActivityLog.Action.CREATE, obj, "Digital partner added.")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._log(ActivityLog.Action.UPDATE, obj, "Digital partner updated.")

    def perform_destroy(self, instance):
        self._log(ActivityLog.Action.DELETE, instance, "Digital partner removed.")
        instance.delete()


class AdminWebsiteThemeViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "pages"
    queryset = WebsiteTheme.objects.all().order_by("-start_date", "name")
    serializer_class = WebsiteThemeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["start_date", "end_date", "name", "is_active"]

    def perform_create(self, serializer):
        obj = serializer.save()
        self._log(ActivityLog.Action.CREATE, obj, "Theme created.")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._log(ActivityLog.Action.UPDATE, obj, "Theme updated.")

    def perform_destroy(self, instance):
        self._log(ActivityLog.Action.DELETE, instance, "Theme removed.")
        instance.delete()


BACKUP_COMPONENT_CHOICES = {
    "database": "Database (content, users and settings)",
    "media": "Media files (images and documents)",
}


def _normalise_components(raw):
    """Return a clean, ordered list of selected backup components."""
    if raw in (None, "", []):
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple, set)):
        return []
    chosen = []
    for item in raw:
        text = str(item).strip().lower()
        if text in BACKUP_COMPONENT_CHOICES and text not in chosen:
            chosen.append(text)
    return chosen


def _backup_type_from_components(components):
    chosen = set(components)
    if chosen == {"database", "media"}:
        return BackupRecord.BackupType.FULL
    if chosen == {"database"}:
        return BackupRecord.BackupType.DATABASE
    if chosen == {"media"}:
        return BackupRecord.BackupType.MEDIA
    return BackupRecord.BackupType.SELECTIVE


def _backup_metadata(file_obj):
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        with zipfile.ZipFile(file_obj, "r") as zf:
            for name in zf.namelist():
                if name.endswith("metadata.json"):
                    return json.loads(zf.read(name).decode("utf-8"))
    except Exception:
        pass
    return {}


def _infer_components(file_obj):
    meta = _backup_metadata(file_obj)
    kind = meta.get("backup_type")
    if kind == "database":
        return ["database"]
    if kind == "media":
        return ["media"]
    names = []
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        with zipfile.ZipFile(file_obj, "r") as zf:
            names = zf.namelist()
    except Exception:
        pass
    has_db = any(n.endswith("database.json") or n.endswith("db.sqlite3") for n in names)
    has_media = any("/media/" in n and not n.endswith("/") for n in names)
    if has_db and has_media:
        return ["database", "media"]
    if has_db:
        return ["database"]
    if has_media:
        return ["media"]
    return []


def _safe_backup_name(filename):
    return Path(filename).name


class AdminBackupView(APIView):
    permission_classes = [ModulePermission]
    permission_module = "backup"

    def _sync_disk_records(self):
        """Register archives that exist on disk but are missing from the table.

        Two dashboard requests can arrive at the same moment (for example the
        React development double-render). `get_or_create` plus the unique
        filename constraint keeps the history free of duplicate rows.
        """
        output_dir = settings.BACKUP_ROOT
        if not output_dir.exists():
            return
        for f in output_dir.glob("*.zip"):
            components = _infer_components(f)
            try:
                BackupRecord.objects.get_or_create(
                    filename=f.name,
                    defaults={
                        "backup_type": _backup_type_from_components(components),
                        "components": components,
                        "size": f.stat().st_size,
                        "status": BackupRecord.Status.SUCCESS,
                        "storage": "server",
                    },
                )
            except IntegrityError:
                # Another request registered this archive first.
                continue

    def _apply_retention(self):
        """Delete the oldest backups above the configured retention limit."""
        try:
            keep = int(SiteSetting.load().backup_retention or 0)
        except Exception:
            keep = 0
        if keep <= 0:
            return
        records = list(
            BackupRecord.objects.filter(status=BackupRecord.Status.SUCCESS)
            .exclude(filename="")
            .order_by("-created_at")
        )
        for record in records[keep:]:
            file_path = settings.BACKUP_ROOT / _safe_backup_name(record.filename)
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError:
                continue
            record.delete()

    def get(self, request):
        self._sync_disk_records()
        qs = BackupRecord.objects.all()
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(filename__icontains=search)
                | Q(created_by__email__icontains=search)
                | Q(created_by__full_name__icontains=search)
            )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        type_filter = request.query_params.get("type")
        if type_filter:
            qs = qs.filter(backup_type=type_filter)
        return Response(BackupRecordSerializer(qs, many=True).data)

    def post(self, request):
        has_components_key = "components" in request.data
        components = _normalise_components(request.data.get("components"))
        if not components and not has_components_key and request.data.get("type"):
            # Backwards compatibility for older clients that posted a single
            # "type" value instead of a component list.
            legacy = str(request.data.get("type") or "full").lower()
            components = (
                ["database", "media"]
                if legacy == "full"
                else _normalise_components([legacy])
            )
        if not components:
            return Response(
                {
                    "detail": (
                        "Choose at least one component to back up: the database, "
                        "media files, or both."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        backup_type = _backup_type_from_components(components)
        output_dir = settings.BACKUP_ROOT
        output_dir.mkdir(parents=True, exist_ok=True)
        before = {f.resolve() for f in output_dir.glob("*.zip")}

        from io import StringIO

        args = ["backup"]
        if components == ["database"]:
            args.append("--database-only")
        elif components == ["media"]:
            args.append("--media-only")
        args.extend(["--output", str(output_dir)])

        try:
            call_command(*args, stdout=StringIO())
        except Exception as exc:
            record = BackupRecord.objects.create(
                filename="",
                backup_type=backup_type,
                components=components,
                status=BackupRecord.Status.FAILED,
                error=f"{type(exc).__name__}: {exc}"[:2000],
                storage="server",
                created_by=request.user,
            )
            log_activity(
                request,
                ActivityLog.Action.BACKUP,
                "backup",
                record,
                "Backup attempt",
                "Backup failed: " + str(exc)[:300],
            )
            return Response(
                {
                    "detail": (
                        "The backup could not be completed. The failure has been "
                        "recorded in the backup history and the server logs."
                    ),
                    "id": record.id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        created = [f for f in output_dir.glob("*.zip") if f.resolve() not in before]
        if not created:
            created = list(output_dir.glob("*.zip"))
        if not created:
            record = BackupRecord.objects.create(
                filename="",
                backup_type=backup_type,
                components=components,
                status=BackupRecord.Status.FAILED,
                error="The backup command finished but produced no archive.",
                storage="server",
                created_by=request.user,
            )
            log_activity(
                request, ActivityLog.Action.BACKUP, "backup", record,
                "Backup attempt", "No archive was produced.",
            )
            return Response(
                {"detail": "The backup finished without producing a file. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        latest = max(created, key=lambda f: f.stat().st_mtime)
        record = BackupRecord.objects.create(
            filename=latest.name,
            backup_type=backup_type,
            components=components,
            size=latest.stat().st_size,
            status=BackupRecord.Status.SUCCESS,
            storage="server",
            created_by=request.user,
        )
        self._apply_retention()
        log_activity(
            request,
            ActivityLog.Action.BACKUP,
            "backup",
            record,
            latest.name,
            f"Created {backup_type} backup ({', '.join(components)}).",
        )
        return Response(
            {
                "detail": "Backup created successfully.",
                "id": record.id,
                "filename": latest.name,
                "size": latest.stat().st_size,
            }
        )


class AdminBackupDownloadView(APIView):
    permission_classes = [ModulePermission]
    permission_module = "backup"

    def get(self, request, pk):
        record = get_object_or_404(BackupRecord, pk=pk)
        if not record.filename:
            return Response(
                {"detail": "This backup record has no archive attached."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file_path = settings.BACKUP_ROOT / _safe_backup_name(record.filename)
        if not file_path.exists():
            return Response(
                {"detail": "Backup file not found on disk."},
                status=status.HTTP_404_NOT_FOUND,
            )
        log_activity(
            request,
            ActivityLog.Action.BACKUP,
            "backup",
            record,
            record.filename,
            "Downloaded backup archive.",
        )
        def file_chunks(path, chunk_size=65536):
            with open(path, "rb") as source:
                while True:
                    chunk = source.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        from django.http import StreamingHttpResponse

        response = StreamingHttpResponse(
            file_chunks(file_path), content_type="application/zip"
        )
        response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
        return response


class AdminBackupDeleteView(APIView):
    permission_classes = [ModulePermission]
    permission_module = "backup"
    permission_action = "delete"

    def delete(self, request, pk):
        record = get_object_or_404(BackupRecord, pk=pk)
        filename = record.filename
        file_path = (
            settings.BACKUP_ROOT / _safe_backup_name(filename) if filename else None
        )
        try:
            if file_path and file_path.is_file():
                file_path.unlink()
        except OSError as exc:
            return Response(
                {"detail": f"The backup file could not be deleted: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        record.delete()
        log_activity(
            request,
            ActivityLog.Action.DELETE,
            "backup",
            None,
            filename or "Backup record",
            "Deleted backup archive and its history record.",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminBackupRestoreView(APIView):
    permission_classes = [ModulePermission]
    permission_module = "backup"
    # Restoring overwrites live data, so it is treated as a destructive action
    # rather than a normal create.
    permission_action = "delete"

    def post(self, request, pk):
        record = get_object_or_404(BackupRecord, pk=pk)
        if not record.filename:
            return Response(
                {"detail": "This backup record has no archive attached."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        file_path = settings.BACKUP_ROOT / _safe_backup_name(record.filename)
        if not file_path.exists():
            return Response(
                {"detail": "Backup file not found on disk."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate before touching any existing data.
        if not zipfile.is_zipfile(file_path):
            return Response(
                {"detail": "This file is not a valid backup archive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        max_uncompressed = getattr(
            settings, "BACKUP_MAX_RESTORE_BYTES", 4 * 1024 * 1024 * 1024
        )
        with zipfile.ZipFile(file_path, "r") as zf:
            infos = zf.infolist()
            if len(infos) > 200000:
                return Response(
                    {"detail": "This archive contains too many files to restore safely."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if sum(info.file_size for info in infos) > max_uncompressed:
                return Response(
                    {"detail": "This archive is larger than the restore limit."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            names = zf.namelist()
            db_files = [n for n in names if n.endswith("database.json")]
            media_files = [
                n
                for n in names
                if "/media/" in n and not n.endswith("/") and ".." not in n.split("/")
            ]
            if not db_files and not media_files:
                return Response(
                    {"detail": "This archive does not contain a database or media files."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if db_files:
                try:
                    json.loads(zf.read(db_files[0]).decode("utf-8"))
                except Exception:
                    return Response(
                        {"detail": "The database inside this archive is not valid JSON."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Create a safety backup before changing live data.
        output_dir = settings.BACKUP_ROOT
        output_dir.mkdir(parents=True, exist_ok=True)
        before = {f.resolve() for f in output_dir.glob("*.zip")}
        from io import StringIO

        try:
            call_command("backup", "--output", str(output_dir), stdout=StringIO())
            created = [f for f in output_dir.glob("*.zip") if f.resolve() not in before]
            if not created:
                raise RuntimeError("the backup command did not produce an archive")
            safety_file = max(created, key=lambda f: f.stat().st_mtime)
            BackupRecord.objects.create(
                filename=safety_file.name,
                backup_type=BackupRecord.BackupType.FULL,
                components=["database", "media"],
                size=safety_file.stat().st_size,
                status=BackupRecord.Status.SUCCESS,
                storage="server",
                created_by=request.user,
            )
        except Exception as exc:
            log_activity(
                request,
                ActivityLog.Action.BACKUP,
                "backup",
                record,
                record.filename,
                f"Restore cancelled because the safety backup failed: {str(exc)[:300]}",
            )
            return Response(
                {
                    "detail": (
                        "Restore cancelled: a safety backup could not be created. "
                        "No data was changed."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        restored = []
        db_file = settings.BACKUP_ROOT / "_restore_db.json"
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                if db_files:
                    db_file.write_bytes(zf.read(db_files[0]))
                    from django.core.management import call_command as run_command

                    run_command("loaddata", str(db_file), verbosity=0)
                    restored.append("database")
                media_root = Path(settings.MEDIA_ROOT).resolve()
                media_root.mkdir(parents=True, exist_ok=True)
                restored_media = 0
                for media_name in media_files:
                    parts = media_name.split("/media/", 1)
                    if len(parts) != 2 or not parts[1]:
                        continue
                    target = (media_root / parts[1]).resolve()
                    if target != media_root and media_root not in target.parents:
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(media_name))
                    restored_media += 1
                if restored_media:
                    restored.append(f"media ({restored_media} files)")
        except Exception as exc:
            log_activity(
                request,
                ActivityLog.Action.BACKUP,
                "backup",
                record,
                record.filename,
                f"Restore failed: {str(exc)[:300]}",
            )
            return Response(
                {
                    "detail": (
                        "The backup was validated but could not be restored. "
                        "Your safety backup is available in the backup list. "
                        f"Reason: {str(exc)[:300]}"
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if db_file.exists():
                db_file.unlink()

        record.restored_at = timezone.now()
        record.restored_by = request.user
        record.save(update_fields=["restored_at", "restored_by"])
        log_activity(
            request,
            ActivityLog.Action.BACKUP,
            "backup",
            record,
            record.filename,
            f"Restored {', '.join(restored) if restored else 'nothing'}. A safety backup was created first.",
        )

        return Response(
            {
                "detail": f"Restored: {', '.join(restored) if restored else 'nothing'}",
                "restored": restored,
            }
        )


class AdminBackupUploadView(APIView):
    permission_classes = [ModulePermission]
    permission_module = "backup"

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response(
                {"detail": "Choose a backup file to upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        safe_name = _safe_backup_name(uploaded.name)
        if not safe_name.lower().endswith(".zip"):
            return Response(
                {"detail": "Only .zip backup archives are accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if getattr(uploaded, "size", 0) > settings.BACKUP_MAX_UPLOAD_BYTES:
            limit_mb = settings.BACKUP_MAX_UPLOAD_BYTES // (1024 * 1024)
            return Response(
                {"detail": f"This file is too large. The upload limit is {limit_mb} MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uploaded.seek(0)
            valid_zip = zipfile.is_zipfile(uploaded)
        except Exception:
            valid_zip = False
        if not valid_zip:
            return Response(
                {"detail": "This file is not a valid .zip archive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        components = _infer_components(uploaded)
        if not components:
            return Response(
                {
                    "detail": (
                        "This archive does not contain a KLB database dump or media "
                        "folder. It was not uploaded."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_dir = settings.BACKUP_ROOT
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / safe_name
        counter = 2
        while dest.exists():
            dest = output_dir / f"{Path(safe_name).stem}-{counter}.zip"
            counter += 1

        uploaded.seek(0)
        with open(dest, "wb") as f:
            for chunk in uploaded.chunks():
                f.write(chunk)

        record = BackupRecord.objects.create(
            filename=dest.name,
            backup_type=_backup_type_from_components(components),
            components=components,
            size=dest.stat().st_size,
            status=BackupRecord.Status.SUCCESS,
            storage="server",
            created_by=request.user,
        )
        log_activity(
            request,
            ActivityLog.Action.BACKUP,
            "backup",
            record,
            dest.name,
            f"Uploaded backup archive ({', '.join(components)}).",
        )
        return Response(
            {
                "detail": "Backup uploaded successfully.",
                "id": record.id,
                "filename": dest.name,
                "size": dest.stat().st_size,
                "components": components,
            }
        )


class AdminAIDraftView(APIView):
    permission_classes = [IsStaff]

    def get_permissions(self):
        return [IsStaff()]

    def post(self, request):
        api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("EDENAI_API_KEY", "") or os.getenv("GROQ_API_KEY", "") or os.getenv("GEMINI_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
        api_key = api_key.strip()
        if not api_key:
            return Response(
                {"detail": "AI API key not configured. Set OPENAI_API_KEY, EDENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY in environment variables."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        topic = (request.data.get("topic") or "").strip()
        if not topic:
            return Response({"detail": "Please provide a topic."}, status=status.HTTP_400_BAD_REQUEST)

        import json as _json
        import urllib.request

        prompt = (
            "Write a short news article for Kenya Literature Bureau PLC about: " + topic + ". "
            "Return ONLY valid JSON with these fields: "
            '{"title": "headline", "summary": "1-2 sentences", "body_html": "<p>paragraph1</p><p>paragraph2</p>"} '
            "The article should be 150-250 words total. Use professional language. "
            "No placeholder text. No explanations outside JSON. Output only the JSON object."
        )

        is_eden = api_key.startswith("sk-eden-")
        is_groq = api_key.startswith("gsk_") or api_key.startswith("sgsk_")
        is_gemini = api_key.startswith("AIza") or api_key.startswith("AQ.")
        is_openrouter = api_key.startswith("sk-or-")
        model = None

        if is_eden:
            url = "https://api.edenai.run/v2/text/chat"
            payload = _json.dumps({
                "providers": "openai",
                "text": prompt,
                "temperature": 0.7,
                "max_tokens": 500,
            }).encode("utf-8")
        elif is_groq:
            model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = _json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500,
            }).encode("utf-8")
        elif is_gemini:
            model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = _json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500},
            }).encode("utf-8")
        elif is_openrouter:
            model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free")
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = _json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500,
                "reasoning": {"effort": "none"},
            }).encode("utf-8")
        else:
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            url = "https://api.openai.com/v1/chat/completions"
            payload = _json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500,
            }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "KLB-Website/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_body = resp.read()
                if not raw_body:
                    return Response(
                        {"detail": "AI service returned an empty response. Try a different model or try again later."},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )
                result = _json.loads(raw_body.decode("utf-8"))
            if is_eden:
                provider_result = result.get("openai", {})
                content = provider_result.get("generated_text", "")
                if not content:
                    content = str(result)
            elif is_gemini:
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = parts[0].get("text", "") if parts else ""
                if not content:
                    content = str(result)
            else:
                msg = result["choices"][0]["message"]
                content = msg.get("content") or ""
                if not content:
                    reasoning_val = msg.get("reasoning")
                    if reasoning_val:
                        content = reasoning_val
                if not content:
                    content = str(result)

            # Try to parse JSON from the content
            try:
                clean = content.strip()
                # Look for JSON object in the content (handles markdown wrapping)
                json_match = re.search(r'\{.*"title".*"summary".*"body_html".*\}', clean, re.DOTALL)
                if json_match:
                    clean = json_match.group(0)
                elif clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                    clean = clean.strip()
                draft = _json.loads(clean)
                if isinstance(draft, dict) and "title" in draft:
                    draft_title = str(draft.get("title", ""))
                    draft_summary = str(draft.get("summary", ""))
                    # Only accept if it has real content (not just echoing the prompt)
                    if len(draft_summary) > 10:
                        return Response({"draft": draft, "model_used": model})
            except (_json.JSONDecodeError, Exception):
                pass

            # If we got content but not valid JSON, wrap it as a draft
            if content and len(content) > 50:
                # Check if content is just echoing the prompt or reasoning
                echo_phrases = [
                    "analyze the request", "constraints:", "output:", "the user wants",
                    "we need to", "requirements:", "return only", "topic:",
                    "your headline", "your paragraph", "we need to produce",
                    "json format", "150-250 words", "no placeholder", "no explanations",
                ]
                is_echo = any(phrase in content.lower() for phrase in echo_phrases)
                if not is_echo:
                    draft = {
                        "title": topic,
                        "summary": content[:200],
                        "body_html": f"<p>{content}</p>",
                    }
                    return Response({"draft": draft, "model_used": model})

            return Response(
                {"detail": "AI service returned insufficient content. Try a different model."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            if "UNAUTHENTICATED" in error_body or "API keys are not supported" in error_body:
                return Response(
                    {"detail": "Your API key is not a valid Gemini key. Get a new key from https://aistudio.google.com/apikey (should start with 'AIza')."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"detail": f"AI API error: {error_body[:300]}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            return Response(
                {"detail": f"Failed to generate draft: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminEnquiryViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "enquiries"
    queryset = Enquiry.objects.all()
    serializer_class = EnquirySerializer
    http_method_names = ["get", "patch", "put", "delete", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "subject", "message"]
    ordering_fields = ["created_at", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AdminSubscriberViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "subscribers"
    queryset = Subscriber.objects.all()
    serializer_class = SubscriberSerializer
    http_method_names = ["get", "delete", "head", "options"]
    filter_backends = [filters.SearchFilter]
    search_fields = ["email"]


class AdminSiteSettingView(APIView):
    permission_classes = [ModulePermission]
    permission_module = "settings"

    CRITICAL_FIELDS = {"navigation", "footer_columns"}

    def get(self, request):
        return Response(SiteSettingSerializer(SiteSetting.load()).data)

    def patch(self, request):
        changed = set(request.data.keys())
        critical = changed & self.CRITICAL_FIELDS
        if critical and not request.user.is_super_administrator:
            return Response(
                {
                    "detail": (
                        "Only a Super Administrator can change the navigation "
                        "structure or footer columns."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        instance = SiteSetting.load()
        serializer = SiteSettingSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_activity(
            request,
            ActivityLog.Action.SETTINGS,
            "settings",
            instance,
            "Site settings",
            f"Updated: {', '.join(sorted(changed))}.",
        )
        return Response(serializer.data)


class AdminDropdownOptionViewSet(AdminActivityMixin, viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "options"
    queryset = DropdownOption.objects.all()
    serializer_class = DropdownOptionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["label", "value"]
    ordering_fields = ["group", "sort_order", "label"]

    def get_permissions(self):
        # Every active staff account needs the active option groups so that
        # dashboard forms can render their dropdowns. Managing options still
        # requires the options module below.
        if self.action == "groups":
            return [IsStaff()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        group = self.request.query_params.get("group")
        if group:
            qs = qs.filter(group=group)
        active = self.request.query_params.get("active")
        if active in {"1", "true"}:
            qs = qs.filter(is_active=True)
        return qs

    def _label(self, obj):
        return f"{obj.get_group_display()}: {obj.label}"

    @action(detail=False, methods=["get"], url_path="groups")
    def groups(self, request):
        include_inactive = request.query_params.get("all") in {"1", "true", "True"}
        qs = DropdownOption.objects.all()
        if not include_inactive:
            qs = qs.filter(is_active=True)
        grouped = {}
        for option in qs:
            grouped.setdefault(option.group, []).append(
                {"value": option.value, "label": option.label}
            )
        return Response(
            {
                "groups": [
                    {"key": key, "label": label, "options": grouped.get(key, [])}
                    for key, label in DropdownOption.Group.choices
                ],
                "options": grouped,
            }
        )

    def perform_create(self, serializer):
        obj = serializer.save()
        self._log(ActivityLog.Action.CREATE, obj, "Dropdown option added.")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._log(ActivityLog.Action.UPDATE, obj, "Dropdown option updated.")

    def perform_destroy(self, instance):
        self._log(ActivityLog.Action.DELETE, instance, "Dropdown option removed.")
        instance.delete()
