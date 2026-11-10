from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve as serve_media
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    ActivityLogViewSet,
    AdminUserViewSet,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PermissionMetaView,
)
from apps.catalogue.views import BookViewSet, CatalogueFiltersView
from apps.content.views import (
    AdminBookViewSet,
    AdminCareerViewSet,
    AdminDigitalPartnerViewSet,
    AdminDropdownOptionViewSet,
    AdminEnquiryViewSet,
    AdminNewsViewSet,
    AdminPageViewSet,
    AdminResourceViewSet,
    AdminSiteSettingView,
    AdminStatsView,
    AdminSubscriberViewSet,
    AdminTeamPhotoView,
    AdminTenderViewSet,
    CareersView,
    DigitalPartnersView,
    NewsViewSet,
    PageDetailView,
    ResourcesView,
    SiteView,
    TendersView,
)
from apps.enquiries.views import NewsletterView, PublicEnquiryView
from apps.content.uploads import MediaUploadView

from .views import health, robots_txt, serve_spa, sitemap_xml

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
public_router = DefaultRouter()
public_router.register("books", BookViewSet, basename="book")
public_router.register("news", NewsViewSet, basename="news")

# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------
admin_router = DefaultRouter()
admin_router.register("pages", AdminPageViewSet, basename="admin-page")
admin_router.register("books", AdminBookViewSet, basename="admin-book")
admin_router.register("news", AdminNewsViewSet, basename="admin-news")
admin_router.register("careers", AdminCareerViewSet, basename="admin-career")
admin_router.register("tenders", AdminTenderViewSet, basename="admin-tender")
admin_router.register("resources", AdminResourceViewSet, basename="admin-resource")
admin_router.register("enquiries", AdminEnquiryViewSet, basename="admin-enquiry")
admin_router.register("subscribers", AdminSubscriberViewSet, basename="admin-subscriber")
admin_router.register("users", AdminUserViewSet, basename="admin-user")
admin_router.register("activity", ActivityLogViewSet, basename="admin-activity")
admin_router.register("options", AdminDropdownOptionViewSet, basename="admin-option")

urlpatterns = [
    # Auth
    path("api/auth/csrf/", CsrfView.as_view(), name="csrf"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/password/", PasswordChangeView.as_view(), name="password-change"),

    # Public content
    path("api/site/", SiteView.as_view(), name="site"),
    path("api/pages/<slug:slug>/", PageDetailView.as_view(), name="page-detail"),
    path("api/catalogue/filters/", CatalogueFiltersView.as_view(), name="catalogue-filters"),
    path("api/careers/", CareersView.as_view(), name="careers"),
    path("api/tenders/", TendersView.as_view(), name="tenders"),
    path("api/resources/", ResourcesView.as_view(), name="resources"),
    path("api/digital-partners/", DigitalPartnersView.as_view(), name="digital-partners"),

    # Public forms
    path("api/enquiries/", PublicEnquiryView.as_view(), name="enquiries"),
    path("api/newsletter/", NewsletterView.as_view(), name="newsletter"),

    # Dashboard
    path("api/admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("api/admin/settings/", AdminSiteSettingView.as_view(), name="admin-settings"),
    path("api/admin/permissions/", PermissionMetaView.as_view(), name="admin-permissions"),
    path("api/admin/upload/", MediaUploadView.as_view(), name="admin-upload"),
    path("api/admin/digital-partners/", AdminDigitalPartnerViewSet.as_view({"get": "list", "post": "create"}), name="admin-digital-partners"),
    path("api/admin/digital-partners/<int:pk>/", AdminDigitalPartnerViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="admin-digital-partner"),
    path("api/admin/team-photos/", AdminTeamPhotoView.as_view(), name="admin-team-photos"),
    path("api/admin/team-photos/<str:key>/", AdminTeamPhotoView.as_view(), name="admin-team-photo"),
    path("api/admin/", include(admin_router.urls)),

    # Public read-only routers
    path("api/", include(public_router.urls)),

    # SEO and health
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("robots.txt", robots_txt, name="robots"),
    path("health/", health, name="health"),
]

# Uploaded media is served by Django so that images keep working on hosts
# without a separate object store. In production a persistent disk must be
# mounted at MEDIA_ROOT (see docs/DEPLOYMENT-RENDER.md).
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve_media, {"document_root": settings.MEDIA_ROOT}),
]

# Everything else is the React single-page application. API, static and media
# requests are excluded so that missing files still return a real 404 rather
# than the app shell.
urlpatterns += [
    re_path(r"^(?P<path>(?!api/|static/|media/).*)$", serve_spa, name="spa"),
]
