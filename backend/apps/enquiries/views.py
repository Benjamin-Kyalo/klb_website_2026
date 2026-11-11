from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Enquiry, Subscriber
from .serializers import PublicEnquirySerializer, SubscriberSerializer


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
        serializer.save()
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
