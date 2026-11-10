import os
import uuid

from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.activity import log_activity
from apps.accounts.models import ActivityLog
from apps.accounts.permissions import CanUploadFiles

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}
MAX_SIZE = 8 * 1024 * 1024


class MediaUploadView(APIView):
    """Small upload endpoint used by the dashboard for covers and PDFs."""

    permission_classes = [CanUploadFiles]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Choose a file to upload."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > MAX_SIZE:
            return Response({"detail": "Files must be 8 MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)

        extension = os.path.splitext(upload.name)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            return Response(
                {"detail": "Allowed file types: JPG, PNG, WebP, GIF and PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filename = f"uploads/{uuid.uuid4().hex}{extension}"
        saved_name = default_storage.save(filename, upload)
        log_activity(
            request,
            ActivityLog.Action.CREATE,
            "media",
            None,
            upload.name,
            f"Uploaded {upload.name}.",
        )
        return Response(
            {
                "url": default_storage.url(saved_name),
                "name": upload.name,
                "size": upload.size,
            },
            status=status.HTTP_201_CREATED,
        )
