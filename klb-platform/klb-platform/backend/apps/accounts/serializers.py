from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.text import slugify
from rest_framework import serializers

from .models import ActivityLog, User
from .rbac import effective_permissions, normalise_permissions


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    role_label = serializers.ReadOnlyField()
    is_administrator = serializers.ReadOnlyField()
    is_super_administrator = serializers.ReadOnlyField()
    can_sign_in = serializers.ReadOnlyField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "display_name", "role",
            "role_label", "is_administrator", "is_super_administrator",
            "is_suspended", "is_active", "can_sign_in", "permissions",
            "last_login", "date_joined",
        ]
        read_only_fields = ["last_login", "date_joined"]

    def get_permissions(self, obj):
        return effective_permissions(obj)


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, min_length=10
    )
    permissions = serializers.JSONField(required=False)
    username = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "role", "is_active",
            "is_suspended", "permissions", "password",
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _actor(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def _actor_is_super(self):
        actor = self._actor()
        return bool(actor and actor.is_authenticated and actor.is_super_administrator)

    def _target_role(self, attrs):
        return attrs.get("role", getattr(self.instance, "role", User.Role.EDITOR))

    def validate_email(self, value):
        value = (value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("An email address is required.")
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        value = (value or "").strip()
        if not value:
            return value
        qs = User.objects.filter(username__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("That username is already taken.")
        return value

    def validate(self, attrs):
        actor = self._actor()
        if not actor:
            return attrs

        target_role = self._target_role(attrs)
        current_role = getattr(self.instance, "role", None)

        if not self._actor_is_super():
            # Administrators may only manage editor accounts and may never
            # grant a higher role or system modules.
            if current_role and current_role != User.Role.EDITOR:
                raise serializers.ValidationError(
                    "Administrators can only manage editor accounts."
                )
            if target_role != User.Role.EDITOR:
                raise serializers.ValidationError(
                    {"role": "Administrators can only assign the Editor role."}
                )

        if self.instance and self.instance == actor:
            if target_role != current_role:
                raise serializers.ValidationError(
                    {"role": "You cannot change your own role."}
                )
            if attrs.get("is_active") is False:
                raise serializers.ValidationError(
                    {"is_active": "You cannot deactivate the account you are signed in with."}
                )
            if attrs.get("is_suspended") is True:
                raise serializers.ValidationError(
                    {"is_suspended": "You cannot suspend the account you are signed in with."}
                )

        if "permissions" in attrs:
            try:
                attrs["permissions"] = normalise_permissions(attrs["permissions"], target_role)
            except ValueError as exc:
                raise serializers.ValidationError({"permissions": str(exc)})

        # Keep the last super administrator in place.
        if self.instance and current_role == User.Role.SUPER_ADMIN and target_role != User.Role.SUPER_ADMIN:
            remaining = User.objects.filter(role=User.Role.SUPER_ADMIN).exclude(pk=self.instance.pk)
            if not remaining.exists():
                raise serializers.ValidationError(
                    {"role": "The last Super Administrator cannot be demoted."}
                )

        if self.instance and current_role == User.Role.SUPER_ADMIN and attrs.get("is_active") is False:
            remaining = (
                User.objects.filter(role=User.Role.SUPER_ADMIN, is_active=True)
                .exclude(pk=self.instance.pk)
            )
            if not remaining.exists():
                raise serializers.ValidationError(
                    {"is_active": "The last active Super Administrator cannot be deactivated."}
                )

        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "A password is required."})
        return attrs

    def _password_error(self, password, user):
        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

    def create(self, validated_data):
        password = validated_data.pop("password", "") or ""
        username = (validated_data.get("username") or "").strip()
        if not username:
            base = slugify(validated_data.get("email", "").split("@")[0]) or "user"
            candidate = base
            counter = 2
            while User.objects.filter(username__iexact=candidate).exists():
                candidate = f"{base}{counter}"
                counter += 1
            username = candidate
        validated_data["username"] = username
        user = User(**validated_data)
        if password:
            self._password_error(password, user)
        user.set_password(password)
        user.is_staff = True
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", "") or ""
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            self._password_error(password, instance)
            instance.set_password(password)
        instance.save()
        return instance


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=10, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        identifier = attrs.get("email", "").strip()
        user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=attrs.get("password"),
        )
        if user is None:
            # also allow signing in with the e-mail address
            try:
                candidate = User.objects.get(email__iexact=identifier)
                user = authenticate(
                    request=self.context.get("request"),
                    username=candidate.username,
                    password=attrs.get("password"),
                )
            except User.DoesNotExist:
                user = None
        if user is None:
            raise serializers.ValidationError("The email or password is incorrect.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been disabled.")
        if user.is_suspended:
            raise serializers.ValidationError("This account has been suspended. Contact an administrator.")
        attrs["user"] = user
        return attrs


class ActivityLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            "id", "actor_name", "actor_email", "action", "action_label", "module",
            "object_id", "object_label", "detail", "ip_address", "created_at",
        ]
        read_only_fields = fields
