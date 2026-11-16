from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from django.core.mail import send_mail

from apps.accounts.permissions import ModulePermission
from apps.content.models import SiteSetting

from .models import Enquiry, Subscriber
from .serializers import PublicEnquirySerializer, SubscriberSerializer


def _inquiry_recipient():
    try:
        setting = SiteSetting.load()
    except Exception:
        setting = None
    if setting and getattr(setting, "inquiry_recipient_email", ""):
        return setting.inquiry_recipient_email
    if setting and getattr(setting, "contact_email", ""):
        return setting.contact_email
    return None


class PublicEnquiryView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "enquiry"

    def post(self, request):
        # Simple honeypot: real visitors never fill this hidden field.
        if request.data.get("company_website"):
            return Response({"detail": "Thank you, your enquiry has been received."}, status=status.HTTP_201_CREATED)

        serializer = PublicEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = serializer.save()

        recipient = _inquiry_recipient()
        if recipient:
            try:
                send_mail(
                    subject=f"New website enquiry: {getattr(enquiry, 'subject', '') or 'General enquiry'}",
                    message=(
                        f"Name: {getattr(enquiry, 'name', '')}\n"
                        f"Email: {getattr(enquiry, 'email', '')}\n"
                        f"Phone: {getattr(enquiry, 'phone', '')}\n"
                        f"Subject: {getattr(enquiry, 'subject', '')}\n\n"
                        f"{getattr(enquiry, 'message', '')}"
                    ),
                    from_email=None,
                    recipient_list=[recipient],
                    fail_silently=True,
                )
            except Exception:
                pass

        return Response(
            {
                "detail": "Thank you. Your enquiry has been sent to the KLB team.",
                "enquiry": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class UnsubscribeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "newsletter"

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "Please provide your email address."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            subscriber = Subscriber.objects.get(email__iexact=email)
        except Subscriber.DoesNotExist:
            return Response({"detail": "This email address is not on our list."}, status=status.HTTP_404_NOT_FOUND)
        if not subscriber.is_active:
            return Response({"detail": "You are already unsubscribed."}, status=status.HTTP_200_OK)
        subscriber.is_active = False
        subscriber.save(update_fields=["is_active"])
        return Response({"detail": "You have been unsubscribed. You will no longer receive KLB newsletters."}, status=status.HTTP_200_OK)

class TestInquiryEmailView(APIView):
    permission_classes = [ModulePermission]
    permission_module = "settings"
    # Sending a test message is an edit of the settings, not a create.
    permission_action = "edit"

    def post(self, request):
        from django.conf import settings as django_settings

        recipient = _inquiry_recipient()
        if not recipient:
            return Response(
                {"detail": "No inquiry recipient email is configured. Save one first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            "smtp" in str(django_settings.EMAIL_BACKEND).lower()
            and not getattr(django_settings, "EMAIL_HOST", "")
        ):
            return Response(
                {
                    "detail": (
                        "Email is not configured on this server. Set EMAIL_HOST, "
                        "EMAIL_PORT, EMAIL_HOST_USER and EMAIL_HOST_PASSWORD "
                        "(or EMAIL_BACKEND=console for testing)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        backend = str(django_settings.EMAIL_BACKEND).lower()
        try:
            send_mail(
                subject="KLB inquiry form - test email",
                message="This is a test message confirming that website inquiries will be delivered to this address.",
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Could not send the test email: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Be honest about what actually happened. A console/locmem backend
        # accepts the message without delivering it, so saying "sent" would
        # mislead an administrator testing real delivery.
        if "console" in backend:
            detail = (
                f"SMTP is not configured. The test message was written to the "
                f"server console instead of being delivered to {recipient}. "
                "Set EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER and "
                "EMAIL_HOST_PASSWORD to send real email."
            )
        elif "locmem" in backend:
            detail = (
                f"Test message accepted by the local test backend for {recipient}. "
                "No real email was delivered."
            )
        else:
            detail = f"Test email sent to {recipient}."
        return Response({"detail": detail, "recipient": recipient})


class NewsletterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "newsletter"

    def post(self, request):
        serializer = SubscriberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber = serializer.save()
        created = getattr(serializer, "was_created", True)
        already = getattr(serializer, "already_subscribed", False)
        if already:
            detail = "You are already subscribed to the KLB newsletter."
        elif created:
            detail = "You are on the list. Thank you for subscribing."
        else:
            detail = "You are already on the list. Thank you for subscribing."
        return Response(
            {"detail": detail, "subscriber": {"email": subscriber.email}, "already_subscribed": already},
            status=status.HTTP_200_OK if already else (status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )
