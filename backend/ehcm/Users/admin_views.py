
import secrets
import string
import logging

from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

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
        login_url = request.build_absolute_uri(reverse("login-page"))

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
            send_mail(
                subject="Your EHCM account has been created",

                message=(
                    f"Hello {user.full_name},\n\n"
                    f"Your EHCM account has been created.\n\n"
                    f"Work ID: {user.work_id}\n"
                    f"Temporary password: {temporary_password}\n\n"
                    f"Sign in and set your permanent password: {login_url}\n\n"
                    "You will not need SMS verification for this first-time "
                    "password setup. SMS verification is required on later logins.\n\n"
                    "Please do not share these credentials."
                ),

                from_email=settings.DEFAULT_FROM_EMAIL,

                recipient_list=[user.email],

                fail_silently=False
            )

        except Exception:

            logger.exception(
                "Account notification failed for %s",
                user.work_id
            )

            # The account exists, but the administrator must
            # arrange secure credential delivery.
            return Response(
                {
                    "message": "Account created, but credential delivery failed. Arrange secure delivery before the user logs in.",
                    "user": UserSerializer(user).data
                },
                status=status.HTTP_201_CREATED
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
