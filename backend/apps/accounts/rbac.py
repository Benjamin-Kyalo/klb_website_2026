"""Central permission registry for the KLB content manager.

The registry is the single source of truth for module names, supported
actions and the default matrix for each role. Both the API and the React
client use the same shape:

    {"pages": ["view", "create", "edit", "delete", "publish"], ...}
"""

from rest_framework.exceptions import PermissionDenied

ACTIONS = ("view", "create", "edit", "delete", "publish")

MODULES = {
    "pages": {"label": "Pages", "group": "Content", "actions": ACTIONS},
    "books": {"label": "Catalogue", "group": "Content", "actions": ACTIONS},
    "news": {"label": "News", "group": "Content", "actions": ACTIONS},
    "careers": {"label": "Careers", "group": "Content", "actions": ACTIONS},
    "tenders": {"label": "Tenders", "group": "Content", "actions": ACTIONS},
    "resources": {"label": "Resources", "group": "Content", "actions": ACTIONS},
    "enquiries": {"label": "Enquiries", "group": "Audience", "actions": ("view", "edit")},
    "subscribers": {"label": "Newsletter", "group": "Audience", "actions": ("view", "delete")},
    "settings": {"label": "Site settings", "group": "System", "actions": ("view", "edit")},
    "users": {"label": "Users", "group": "System", "actions": ("view", "create", "edit", "delete")},
    "activity": {"label": "Activity log", "group": "System", "actions": ("view",)},
    "options": {"label": "Dropdown options", "group": "System", "actions": ACTIONS},
    "media": {"label": "File uploads", "group": "Content", "actions": ("view", "create")},
}

CONTENT_MODULES = ("pages", "books", "news", "careers", "tenders", "resources")

# Editors may never be granted these modules, even if somebody hand-edits the
# stored matrix. This is the hard clamp required by the brief.
EDITOR_MODULES = {
    "pages",
    "books",
    "news",
    "careers",
    "tenders",
    "resources",
    "enquiries",
    "subscribers",
    "media",
}

_ADMIN_DEFAULTS = {
    "pages": list(ACTIONS),
    "books": list(ACTIONS),
    "news": list(ACTIONS),
    "careers": list(ACTIONS),
    "tenders": list(ACTIONS),
    "resources": list(ACTIONS),
    "enquiries": ["view", "edit"],
    "subscribers": ["view", "delete"],
    "settings": ["view", "edit"],
    "users": ["view", "create", "edit", "delete"],
    "activity": ["view"],
    "options": list(ACTIONS),
    "media": ["view", "create"],
}

# Editors start with the least privilege they need to write content: they can
# read, create and edit, but deleting and publishing must be granted explicitly
# by an administrator. Dropdown options and system modules stay out of reach.
_EDITOR_DEFAULTS = {
    "pages": ["view", "create", "edit"],
    "books": ["view", "create", "edit"],
    "news": ["view", "create", "edit"],
    "careers": ["view", "create", "edit"],
    "tenders": ["view", "create", "edit"],
    "resources": ["view", "create", "edit"],
    "enquiries": ["view"],
    "subscribers": ["view"],
    "media": ["view", "create"],
}

ROLE_DEFAULTS = {
    "super_admin": {module: list(ACTIONS) for module in MODULES},
    "admin": _ADMIN_DEFAULTS,
    "editor": _EDITOR_DEFAULTS,
}


def all_permissions():
    return {module: list(ACTIONS) for module in MODULES}


def _clamp(module, granted, role):
    allowed_actions = set(MODULES.get(module, {}).get("actions", ()))
    if role == "editor" and module not in EDITOR_MODULES:
        return []
    return [action for action in ACTIONS if action in granted and action in allowed_actions]


def effective_permissions(user):
    """Return the effective module/action matrix for a user."""
    if not user or not getattr(user, "is_authenticated", False):
        return {}
    if not getattr(user, "is_active", True) or getattr(user, "is_suspended", False):
        return {}

    role = getattr(user, "role", "editor")
    if getattr(user, "is_superuser", False) or role == "super_admin":
        return all_permissions()

    stored = getattr(user, "permissions", None)
    base = stored if isinstance(stored, dict) and stored else ROLE_DEFAULTS.get(role, _EDITOR_DEFAULTS)

    result = {}
    for module in MODULES:
        result[module] = _clamp(module, base.get(module, []), role)
    return result


def has_permission(user, module, action):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", True) or getattr(user, "is_suspended", False):
        return False
    if action not in ACTIONS:
        return False
    return action in effective_permissions(user).get(module, [])


def require_permission(user, module, action):
    if not has_permission(user, module, action):
        raise PermissionDenied("Your account does not have permission to perform this action.")


def normalise_permissions(raw, role):
    """Validate and clamp a submitted permission matrix.

    A non-empty dictionary is treated as the complete matrix. Unknown modules
    and actions are dropped so a crafted request cannot widen access.
    """
    if raw in (None, "", {}):
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Permissions must be an object keyed by module.")
    result = {}
    for module in MODULES:
        values = raw.get(module, [])
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, (list, tuple, set)):
            values = []
        result[module] = _clamp(module, set(values), role)
    return result


def module_choices():
    return [
        {
            "key": key,
            "label": meta["label"],
            "group": meta["group"],
            "actions": list(meta["actions"]),
        }
        for key, meta in MODULES.items()
    ]
