from rest_framework import serializers

from .models import Enquiry, Subscriber


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = [
            "id", "name", "email", "phone", "organisation", "enquiry_type",
            "subject", "message", "status", "internal_note", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please enter your name.")
        return value

    def validate_subject(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Please add a short subject.")
        return value

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Please add a little more detail (at least 10 characters).")
        if len(value) > 5000:
            raise serializers.ValidationError("Please keep your message under 5,000 characters.")
        return value


class PublicEnquirySerializer(EnquirySerializer):
    """Fields accepted from the public contact form (no status/note)."""

    class Meta(EnquirySerializer.Meta):
        fields = [
            "id", "name", "email", "phone", "organisation", "enquiry_type",
            "subject", "message", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = ["id", "email", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"email": {"validators": []}}

    def validate_email(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        email = validated_data["email"]
        subscriber, created = Subscriber.objects.get_or_create(
            email__iexact=email,
            defaults={"email": email},
        )
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save(update_fields=["is_active"])
            self.was_created = True
        elif not created and subscriber.is_active:
            self.was_created = False
            self.already_subscribed = True
        else:
            self.was_created = True
            self.already_subscribed = False
        return subscriber
