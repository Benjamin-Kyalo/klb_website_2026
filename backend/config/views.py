"""Site-level helpers: sitemap, robots, health check and the SPA shell."""
import mimetypes
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.utils import timezone

PUBLIC_PATHS = ["/", "/books/", "/news/", "/about/", "/services/", "/digital/", "/resources/", "/careers/", "/tenders/", "/contact/", "/privacy/", "/terms/"]


def sitemap_xml(request):
    """Database-driven sitemap for pages, books and news."""
    from apps.catalogue.models import Book
    from apps.content.models import News, Page

    base = request.build_absolute_uri("/").rstrip("/")
    urls = []

    pages = Page.objects.filter(status=Page.Status.PUBLISHED)
    for page in pages:
        urls.append((f"{base}/{'' if page.slug == 'home' else page.slug + '/'}", page.updated_at.date()))

    for book in Book.objects.filter(is_published=True).only("slug", "updated_at"):
        urls.append((f"{base}/books/{book.slug}/", book.updated_at.date()))

    for article in News.objects.filter(status=News.Status.PUBLISHED).only("slug", "updated_at"):
        urls.append((f"{base}/news/{article.slug}/", article.updated_at.date()))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(loc)}</loc>")
        lines.append(f"    <lastmod>{lastmod.isoformat()}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return HttpResponse("\n".join(lines), content_type="application/xml")


def robots_txt(request):
    base = request.build_absolute_uri("/").rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        f"Sitemap: {base}/sitemap.xml",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def health(request):
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "time": timezone.now().isoformat(), "date": date.today().isoformat()})
    except Exception as exc:  # pragma: no cover - defensive
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)


def serve_spa(request, path=""):
    """Serve the built React app, or a helpful message when it is not built."""
    dist = Path(settings.FRONTEND_DIST)

    # Serve real files from the build output (hashed JS/CSS and public assets).
    if path:
        candidate = (dist / path).resolve()
        try:
            candidate.relative_to(dist.resolve())
        except ValueError:
            raise Http404("Not found")
        if candidate.is_file():
            content_type, _ = mimetypes.guess_type(str(candidate))
            return FileResponse(open(candidate, "rb"), content_type=content_type or "application/octet-stream")

    index = dist / "index.html"
    if index.exists():
        return FileResponse(open(index, "rb"), content_type="text/html")

    return HttpResponse(
        "<!doctype html><html><head><title>KLB website</title></head><body "
        "style='font-family:system-ui;padding:3rem;max-width:42rem;margin:auto;line-height:1.6'>"
        "<h1>KLB website API is running</h1>"
        "<p>The React front end has not been built yet. Run "
        "<code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>, then reload this page.</p>"
        "<p>API health: <a href='/health/'>/health/</a></p>"
        "</body></html>",
        content_type="text/html",
        status=200,
    )
