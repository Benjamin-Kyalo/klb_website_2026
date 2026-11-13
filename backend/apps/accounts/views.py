from django.contrib.auth import login, logout
from django.db.models import Q
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import filters, status, viewsets
from rest_framework.authentication import CSRFCheck
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
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

    EXPORT_HEADERS = ["Date and time", "User", "Email", "Action", "Module", "Record", "Details", "IP address"]

    @staticmethod
    def _safe_cell(value):
        text = "" if value is None else str(value)
        # Prevent spreadsheet formulas from being executed when opened.
        return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text

    @staticmethod
    def _export_row(log):
        return [
            log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else "",
            ActivityLogViewSet._safe_cell(log.actor_name),
            ActivityLogViewSet._safe_cell(log.actor_email),
            ActivityLogViewSet._safe_cell(log.get_action_display()),
            ActivityLogViewSet._safe_cell(log.module),
            ActivityLogViewSet._safe_cell(log.object_label),
            ActivityLogViewSet._safe_cell(log.detail),
            ActivityLogViewSet._safe_cell(log.ip_address or ""),
        ]

    def get_queryset(self):
        from django.utils.dateparse import parse_date

        qs = super().get_queryset()
        params = self.request.query_params
        module = params.get("module")
        if module:
            qs = qs.filter(module=module)
        action_name = params.get("action")
        if action_name:
            qs = qs.filter(action=action_name)
        actor = params.get("actor")
        if actor:
            qs = qs.filter(actor_id=actor)
        date_from = parse_date(params.get("date_from") or "")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        date_to = parse_date(params.get("date_to") or "")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    @action(detail=False, methods=["get"], url_path="actors")
    def actors(self, request):
        """Distinct users who appear in the (optionally filtered) log."""
        rows = (
            self.get_queryset()
            .exclude(actor__isnull=True)
            .values("actor_id", "actor_name", "actor_email")
            .distinct()
            .order_by("actor_name", "actor_email")
        )
        return Response(
            [
                {
                    "id": row["actor_id"],
                    "name": row["actor_name"] or row["actor_email"] or "Unknown user",
                    "email": row["actor_email"],
                }
                for row in rows
            ]
        )

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """Export the filtered activity log as CSV, Excel or PDF."""
        import csv
        import io
        from django.utils import timezone

        fmt = (request.query_params.get("format") or "csv").strip().lower()
        qs = self.filter_queryset(self.get_queryset())
        rows = [self._export_row(log) for log in qs]
        stamp = timezone.now().strftime("%Y%m%d_%H%M")

        if fmt == "xlsx":
            try:
                from openpyxl import Workbook
                from openpyxl.styles import Font
            except ImportError:
                return Response(
                    {"detail": "Excel export is not available on this server. Please use CSV."},
                    status=status.HTTP_501_NOT_IMPLEMENTED,
                )
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Activity log"
            sheet.append(self.EXPORT_HEADERS)
            for cell in sheet[1]:
                cell.font = Font(bold=True)
            for row in rows:
                sheet.append(row)
            widths = [18, 22, 28, 20, 18, 32, 60, 18]
            for index, width in enumerate(widths, start=1):
                sheet.column_dimensions[sheet.cell(row=1, column=index).column_letter].width = width
            sheet.freeze_panes = "A2"
            buffer = io.BytesIO()
            workbook.save(buffer)
            response = HttpResponse(
                buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="activity_log_{stamp}.xlsx"'
        elif fmt == "pdf":
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
                from xml.sax.saxutils import escape
            except ImportError:
                return Response(
                    {"detail": "PDF export is not available on this server. Please use CSV."},
                    status=status.HTTP_501_NOT_IMPLEMENTED,
                )
            buffer = io.BytesIO()
            document = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                leftMargin=24,
                rightMargin=24,
                topMargin=28,
                bottomMargin=28,
            )
            styles = getSampleStyleSheet()
            small = styles["BodyText"].clone("small")
            small.fontSize = 7
            small.leading = 9
            data = [self.EXPORT_HEADERS]
            for row in rows:
                data.append([Paragraph(escape(str(cell)), small) for cell in row])
            table = Table(data, repeatRows=1, colWidths=[62, 78, 100, 66, 62, 110, 180, 64])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#062f4e")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d6e2")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7fa")]),
                    ]
                )
            )
            document.build(
                [
                    Paragraph("Kenya Literature Bureau PLC - activity log", styles["Title"]),
                    Paragraph(
                        f"Generated {timezone.now().strftime('%d %b %Y %H:%M')} - {len(rows)} entries. "
                        "Filters currently applied on the activity log page are reflected in this report.",
                        styles["BodyText"],
                    ),
                    Spacer(1, 10),
                    table,
                ]
            )
            response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="activity_log_{stamp}.pdf"'
        elif fmt == "csv":
            buffer = io.StringIO()
            buffer.write("\ufeff")  # UTF-8 BOM so Excel reads accents correctly.
            writer = csv.writer(buffer)
            writer.writerow(self.EXPORT_HEADERS)
            for row in rows:
                writer.writerow(row)
            response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="activity_log_{stamp}.csv"'
        else:
            return Response(
                {"detail": "Choose a supported export format: csv, xlsx or pdf."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_activity(
            request,
            ActivityLog.Action.EXPORT,
            "activity",
            None,
            "Activity log",
            f"Exported {len(rows)} entries as {fmt.upper()}.",
        )
        return response
