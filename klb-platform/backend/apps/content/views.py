from django.shortcuts import get_object_or_404
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

from .models import Career, DropdownOption, News, Page, Resource, SiteSetting, Tender
from .serializers import (
    CareerSerializer,
    DropdownOptionSerializer,
    NewsSerializer,
    PageDetailSerializer,
    PageListSerializer,
    ResourceSerializer,
    SiteSettingSerializer,
    TenderSerializer,
)


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
        return Response(PageDetailSerializer(page).data)


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
