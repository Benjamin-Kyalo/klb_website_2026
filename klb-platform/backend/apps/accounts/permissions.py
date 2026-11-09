from rest_framework.permissions import BasePermission, SAFE_METHODS

from .rbac import CONTENT_MODULES, MODULES, has_permission

METHOD_ACTIONS = {
    "GET": "view",
    "HEAD": "view",
    "OPTIONS": "view",
    "POST": "create",
    "PUT": "edit",
    "PATCH": "edit",
    "DELETE": "delete",
}


def _is_active_staff(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "is_active", False)
        and not getattr(user, "is_suspended", False)
        and getattr(user, "is_editor", False)
    )


class IsStaff(BasePermission):
    """Any active, non-suspended dashboard account."""

    message = "You need an active staff account to use the content manager."

    def has_permission(self, request, view):
        return _is_active_staff(request.user)


class IsEditor(IsStaff):
    """Backwards-compatible alias used by older imports."""


class IsAdministrator(BasePermission):
    """Administrators and super administrators only."""

    message = "Administrator access is required."

    def has_permission(self, request, view):
        return bool(_is_active_staff(request.user) and request.user.is_administrator)


class IsSuperAdministrator(BasePermission):
    """Super administrators only (critical settings and code-level changes)."""

    message = "Super Administrator access is required."

    def has_permission(self, request, view):
        return bool(_is_active_staff(request.user) and request.user.is_super_administrator)


class ModulePermission(BasePermission):
    """Map the request to View/Create/Edit/Delete on the view's module.

    Viewsets set ``permission_module = "pages"``. A custom action may set
    ``permission_action`` to override the method-derived action.
    """

    message = "Your account does not have permission to perform this action."

    def has_permission(self, request, view):
        if not _is_active_staff(request.user):
            return False

        module = getattr(view, "permission_module", None)
        if not module or module not in MODULES:
            return False

        action = getattr(view, "permission_action", None)
        if not action:
            action = METHOD_ACTIONS.get(request.method, "view")
        return has_permission(request.user, module, action)


class CanUploadFiles(BasePermission):
    """Uploading is allowed when the account can create or edit content."""

    message = "You do not have permission to upload files."

    def has_permission(self, request, view):
        if not _is_active_staff(request.user):
            return False
        for module in CONTENT_MODULES:
            if has_permission(request.user, module, "create") or has_permission(
                request.user, module, "edit"
            ):
                return True
        return has_permission(request.user, "media", "create")


class ReadOnlyOrEditor(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _is_active_staff(request.user)
