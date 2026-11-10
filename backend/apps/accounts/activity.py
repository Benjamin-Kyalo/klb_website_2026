from .models import ActivityLog


def client_ip(request):
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def log_activity(request, action, module, obj=None, label="", detail=""):
    """Record a dashboard change. Failures must never break the request."""
    try:
        user = getattr(request, "user", None) if request else None
        actor = user if user and getattr(user, "is_authenticated", False) else None
        ActivityLog.objects.create(
            actor=actor,
            actor_name=(actor.display_name if actor else "System"),
            actor_email=(actor.email if actor else ""),
            action=action,
            module=module,
            object_id=str(getattr(obj, "pk", "") or "")[:80],
            object_label=(label or str(obj) if obj is not None else label or "")[:255],
            detail=detail,
            ip_address=client_ip(request),
        )
    except Exception:  # pragma: no cover - logging must be best-effort
        import logging

        logging.getLogger(__name__).exception("Could not write activity log entry")
