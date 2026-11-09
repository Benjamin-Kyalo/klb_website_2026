from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A member of staff who can sign in to the content manager.

    Three levels are supported:

    - super administrator: full access, including code-level settings,
      navigation structure and every account.
    - administrator: content oversight, operational settings and management
      of editor accounts.
    - editor: assigned content and audience work only.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Administrator"
        ADMINISTRATOR = "admin", "Administrator"
        EDITOR = "editor", "Editor"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EDITOR)
    full_name = models.CharField(max_length=150, blank=True)
    is_suspended = models.BooleanField(
        default=False,
        help_text="Suspended accounts can sign in but cannot change any content.",
    )
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional per-module permission matrix. Empty means the role defaults apply.",
    )

    REQUIRED_FIELDS = ["email"]

    @property
    def display_name(self) -> str:
        return self.full_name.strip() or self.get_full_name().strip() or self.username

    @property
    def is_super_administrator(self) -> bool:
        return bool(self.is_superuser or self.role == self.Role.SUPER_ADMIN)

    @property
    def is_administrator(self) -> bool:
        return bool(self.is_superuser or self.role in {self.Role.SUPER_ADMIN, self.Role.ADMINISTRATOR})

    @property
    def is_editor(self) -> bool:
        return bool(self.is_administrator or self.role == self.Role.EDITOR)

    @property
    def can_sign_in(self) -> bool:
        return bool(self.is_active and not self.is_suspended)

    @property
    def role_label(self) -> str:
        return self.get_role_display()

    def save(self, *args, **kwargs):
        # A newly created Django superuser is promoted to the highest staff
        # role. Role remains authoritative afterwards so a super administrator
        # can be demoted without the flag silently restoring the role.
        if self._state.adding and self.is_superuser:
            self.role = self.Role.SUPER_ADMIN
        if self.role == self.Role.SUPER_ADMIN:
            self.is_superuser = True
            self.is_staff = True
        else:
            self.is_superuser = False
            self.is_staff = True
        if not self.email:
            self.email = self.username
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.display_name} <{self.email}>"


class ActivityLog(models.Model):
    """An immutable audit entry for a dashboard change."""

    class Action(models.TextChoices):
        CREATE = "create", "Created"
        UPDATE = "update", "Updated"
        DELETE = "delete", "Deleted"
        PUBLISH = "publish", "Published"
        UNPUBLISH = "unpublish", "Unpublished"
        SETTINGS = "settings", "Settings updated"
        USER = "user", "User account changed"
        PASSWORD = "password", "Password reset"

    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_entries",
    )
    actor_name = models.CharField(max_length=180, blank=True)
    actor_email = models.EmailField(blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    module = models.CharField(max_length=40)
    object_id = models.CharField(max_length=80, blank=True)
    object_label = models.CharField(max_length=255, blank=True)
    detail = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["module", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]
        verbose_name = "activity entry"
        verbose_name_plural = "activity log"

    def __str__(self) -> str:
        return f"{self.actor_name or 'System'} {self.get_action_display().lower()} {self.module}"
