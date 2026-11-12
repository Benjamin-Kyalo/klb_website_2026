"""Security and cache-control middleware for the KLB website."""

from django.conf import settings as django_settings
from django.utils.deprecation import MiddlewareMixin


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses."""

    def process_response(self, request, response):
        # Prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response["X-Frame-Options"] = "DENY"
        # Referrer policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions policy
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # Cache control for API responses (prevent stale data)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"

        # Content Security Policy (only in production)
        if not django_settings.DEBUG:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://code.tidio.co https://*.tidio.co; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://code.tidio.co https://*.tidio.co wss://*.tidio.co; "
                "frame-ancestors 'none';"
            )
            response["Content-Security-Policy"] = csp

        return response
