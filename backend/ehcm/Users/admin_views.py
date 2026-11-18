import secrets
import string
import logging

from django.db import transaction
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import User
from .serializers import (
    AdminCreateUserSerializer,
    UserSerializer
)

from .permissions import IsSuperAdmin
from .services.smtp_service import send_temporary_password_email


logger = logging.getLogger(__name__)


def generate_temporary_password(length=14):

    alphabet = string.ascii_letters + string.digits + "!@#$%"

    while True:
        password = "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%" for c in password)
        ):
            return password


class CreateUserView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsSuperAdmin
    ]

    def post(self, request):

        serializer = AdminCreateUserSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        temporary_password = generate_temporary_password()
        login_url = f"{settings.FRONTEND_BASE_URL}/login.html"

        with transaction.atomic():

            user = serializer.save(
                is_active=True,
                must_change_password=True
            )

            user.set_password(temporary_password)

            user.save(
                update_fields=["password"]
            )

            # This is a one-time credential.
            # Do not store it in the database or session.

        try:
            send_temporary_password_email(
                recipient=user.email,
                full_name=user.full_name,
                work_id=user.work_id,
                temporary_password=temporary_password,
                login_url=login_url,
            )

        except Exception:

            logger.exception(
                "Account notification failed for %s",
                user.work_id
            )

            user.is_active = False
            user.save(update_fields=["is_active"])
            return Response(
                {
                    "message": "Credential email failed; the account has been disabled. Correct the email configuration and create the account again.",
                    "user": UserSerializer(user).data
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {
                "message": "Account created successfully. Temporary password sent by email.",
                "user": UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )


class UserListView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsSuperAdmin
    ]

    def get(self, request):

        users = User.objects.all().order_by("-created_at")

        serializer = UserSerializer(
            users,
            many=True
        )

        return Response(serializer.data)


class DeactivateUserView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsSuperAdmin
    ]

    def post(self, request, user_id):

        user = User.objects.filter(
            id=user_id
        ).first()

        if not user:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_superuser:
            return Response(
                {"error": "Cannot deactivate a superuser through this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response({
            "message": "User deactivated successfully."
        })
