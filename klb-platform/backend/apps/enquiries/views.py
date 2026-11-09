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


class NewsletterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "enquiry"

    def post(self, request):
        serializer = SubscriberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber = serializer.save()
        created = getattr(serializer, "was_created", True)
        detail = (
            "You are on the list. Thank you for subscribing."
            if created
            else "You are already on the list. Thank you for subscribing."
        )
        return Response(
            {"detail": detail, "subscriber": {"email": subscriber.email}},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
