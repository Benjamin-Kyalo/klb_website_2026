from django.contrib.auth import login, logout
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import filters, status, viewsets
from rest_framework.authentication import CSRFCheck
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .activity import log_activity
from .models import ActivityLog, User
from .permissions import IsAdministrator, IsStaff, ModulePermission
from .rbac import (
    EDITOR_MODULES,
    ROLE_DEFAULTS,
    effective_permissions,
    module_choices,
    require_permission,
)
from .serializers import (
    ActivityLogSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    UserWriteSerializer,
)


def _enforce_csrf(request):
    """Apply Django's CSRF check to the login request explicitly."""
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("CSRF verification failed. Refresh the page and try again.")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        _enforce_csrf(request)
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Signed out."})


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        if not user.is_authenticated or not getattr(user, "can_sign_in", False):
            return Response({"user": None})
        return Response({"user": UserSerializer(user).data})


class PasswordChangeView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        current = request.data.get("current_password", "")
        new = request.data.get("new_password", "")
        if not request.user.check_password(current):
            return Response({"detail": "Your current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        if len(new) < 10:
            return Response(
                {"detail": "Choose a password with at least 10 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new)
        request.user.save()
        log_activity(request, ActivityLog.Action.PASSWORD, "users", request.user, request.user.display_name)
        login(request, request.user)
        return Response({"detail": "Password updated."})


class PermissionMetaView(APIView):
    """Describe modules and role defaults for the permission editor."""

    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response(
            {
                "modules": module_choices(),
                "roles": [
                    {"value": "super_admin", "label": "Super Administrator"},
                    {"value": "admin", "label": "Administrator"},
                    {"value": "editor", "label": "Editor"},
                ],
                "defaults": {key: value for key, value in ROLE_DEFAULTS.items()},
                "canManageSuperAdmins": request.user.is_super_administrator,
                "editorModules": sorted(EDITOR_MODULES),
            }
        )


class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "users"
    queryset = User.objects.all().order_by("full_name", "email")
    serializer_class = UserWriteSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "email", "username"]
    ordering_fields = ["full_name", "email", "role", "date_joined", "last_login"]

    def get_permissions(self):
        if self.action in {"reset_password", "permissions"}:
            self.permission_action = "edit"
        else:
            self.permission_action = None
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_super_administrator:
            qs = qs.filter(Q(role=User.Role.EDITOR) | Q(pk=user.pk))
        return qs

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return UserSerializer
        return UserWriteSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        log_activity(
            self.request,
            ActivityLog.Action.USER,
            "users",
            user,
            user.display_name,
            f"Created {user.get_role_display()} account {user.email}.",
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        before = {
            "role": instance.role,
            "is_active": instance.is_active,
            "is_suspended": instance.is_suspended,
        }
        password_changed = bool(serializer.validated_data.get("password"))
        user = serializer.save()
        changes = []
        for field, label in (("role", "role"), ("is_active", "active status"), ("is_suspended", "suspension")):
            after = getattr(user, field)
            if before[field] != after:
                changes.append(f"{label}: {before[field]} to {after}")
        detail = "; ".join(changes) or "Account details updated."
        log_activity(self.request, ActivityLog.Action.USER, "users", user, user.display_name, detail)
        if password_changed:
            log_activity(self.request, ActivityLog.Action.PASSWORD, "users", user, user.display_name, "Password reset by an administrator.")

    def perform_destroy(self, instance):
        request = self.request
        if instance == request.user:
            raise ValidationError("You cannot delete the account you are signed in with.")
        if instance.role == User.Role.SUPER_ADMIN:
            remaining = User.objects.filter(role=User.Role.SUPER_ADMIN).exclude(pk=instance.pk)
            if not remaining.exists():
                raise ValidationError("The last Super Administrator cannot be deleted.")
        label = instance.display_name
        log_activity(request, ActivityLog.Action.USER, "users", instance, label, f"Deleted account {instance.email}.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        if not request.user.is_super_administrator and user.role != User.Role.EDITOR:
            raise ValidationError("Administrators can only reset passwords for editors.")
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        log_activity(request, ActivityLog.Action.PASSWORD, "users", user, user.display_name, "Password reset by an administrator.")
        return Response({"detail": f"Password reset for {user.display_name}."})

    @action(detail=False, methods=["get"], url_path="permissions")
    def permissions(self, request):
        return Response(
            {
                "modules": module_choices(),
                "defaults": ROLE_DEFAULTS,
                "canManageSuperAdmins": request.user.is_super_administrator,
                "editorModules": sorted(EDITOR_MODULES),
            }
        )


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ModulePermission]
    permission_module = "activity"
    serializer_class = ActivityLogSerializer
    queryset = ActivityLog.objects.select_related("actor").all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["actor_name", "actor_email", "object_label", "detail"]
    ordering_fields = ["created_at", "action", "module"]

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get("module")
        if module:
            qs = qs.filter(module=module)
        action_name = self.request.query_params.get("action")
        if action_name:
            qs = qs.filter(action=action_name)
        actor = self.request.query_params.get("actor")
        if actor:
            qs = qs.filter(actor_id=actor)
        return qs
