
import logging
import secrets
import string

from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from .models import User

from .serializers import (
    UserSerializer,
    AdminCreateUserSerializer,
    LoginSerializer,
    LoginOTPVerifySerializer,
    ChangePasswordSerializer,
    ProfileUpdateSerializer,
)

from .permissions import (
    IsSuperAdmin,
    PasswordSetupComplete,
)

from .services.otp import (
    generate_otp,
    hash_otp,
    clear_otp,
)

from .services.sms import send_otp_sms


logger = logging.getLogger(__name__)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def generate_temp_password(length=16):

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


def generate_and_send_otp(user):

    otp = generate_otp()

    user.otp_code = hash_otp(otp)

    user.otp_created_at = timezone.now()

    user.otp_attempts = 0

    user.save(
        update_fields=[
            "otp_code",
            "otp_created_at",
            "otp_attempts",
        ]
    )

    try:

        send_otp_sms(
            user.phone_number,
            otp
        )

    except Exception:

        clear_otp(user)

        raise


def generate_jwt_tokens(user):

    refresh = RefreshToken.for_user(user)

    refresh["role"] = user.role
    refresh["email"] = user.email

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


# --------------------------------------------------
# SUPER ADMIN ACCOUNT MANAGEMENT
# --------------------------------------------------

class AdminUserManagementView(viewsets.ViewSet):

    permission_classes = [
        IsAuthenticated,
        IsSuperAdmin,
    ]

    @action(
        detail=False,
        methods=["post"],
        url_path="create-user"
    )
    def create_user(self, request):

        serializer = AdminCreateUserSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        temporary_password = generate_temp_password()

        try:

            with transaction.atomic():

                user = serializer.save(
                    is_active=True,
                    is_staff=False,
                    must_change_password=True,
                )

                user.set_password(temporary_password)

                user.save(
                    update_fields=["password"]
                )

                # Record the administrator responsible for creation
                logger.info(
                    "Account created: user=%s admin=%s",
                    user.id,
                    request.user.id
                )

        except Exception:

            logger.exception("Account creation failed.")

            return Response(
                {"error": "Unable to create account."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    try:
        send_mail(
            subject="EHCM Account Credentials",

            message=(
                f"Hello {user.full_name},\n\n"
                "Your EHCM account has been created successfully.\n\n"
                f"Work ID: {user.work_id}\n"
                f"Temporary password: {temporary_password}\n\n"
                "Login using your Work ID and temporary password.\n\n"
                "A verification OTP will be sent to your registered "
                "phone number.\n\n"
                "After successfulcessful OTP verification, you must create "
                "your own password.\n\n"
                "Please keep your credentials confidential."
            ),

            from_email=settings.DEFAULT_FROM_EMAIL,

            recipient_list=[user.email],

            fail_silently=False,
        )

        logger.info(
            "Account credentials email sent to %s",
            user.email
        )

    except Exception:

        logger.exception(
            "Credential email delivery failed for user %s",
            user.id
        )

        return Response(
            {
                "message": (
                    "Account created, but email delivery failed."
                ),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED
        )


    @action(
        detail=False,
        methods=["get"],
        url_path="list-users"
    )
    def list_users(self, request):

        users = User.objects.exclude(
            role=User.RoleChoices.SUPER_ADMIN
        ).order_by("-created_at")

        serializer = UserSerializer(
            users,
            many=True
        )

        return Response({
            "count": users.count(),
            "users": serializer.data,
        })

    @action(
        detail=True,
        methods=["patch"],
        url_path="deactivate"
    )
    def deactivate_user(self, request, pk=None):

        user = User.objects.filter(
            pk=pk
        ).first()

        if not user:

            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.role == User.RoleChoices.SUPER_ADMIN:

            return Response(
                {"error": "Cannot deactivate a Super Admin here."},
                status=status.HTTP_403_FORBIDDEN
            )

        user.is_active = False

        clear_otp(user)

        user.save(
            update_fields=["is_active"]
        )

        return Response({
            "message": "User account deactivated."
        })

    @action(
        detail=True,
        methods=["patch"],
        url_path="activate"
    )
    def activate_user(self, request, pk=None):

        user = User.objects.filter(
            pk=pk
        ).first()

        if not user:

            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        user.is_active = True

        user.save(
            update_fields=["is_active"]
        )

        return Response({
            "message": "User account activated."
        })


# --------------------------------------------------
# LOGIN - STEP 1
# --------------------------------------------------

class LoginView(viewsets.ViewSet):

    permission_classes = [AllowAny]

    @action(
        detail=False,
        methods=["post"],
        url_path="login"
    )
    def login_user(self, request):

        serializer = LoginSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        try:

            generate_and_send_otp(user)

        except Exception:

            logger.exception(
                "Could not send OTP to user %s",
                user.id
            )

            return Response(
                {
                    "error": "OTP delivery failed. Please try again."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {
                "success": True,
                "message": "OTP sent to your registered phone.",
                "mfa_required": True,
                "email": user.email,
                "phone_number": (
                    "*" * max(
                        0,
                        len(user.phone_number) - 4
                    )
                    + user.phone_number[-4:]
                ),
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# LOGIN - STEP 2: OTP VERIFICATION
# --------------------------------------------------

class LoginOTPView(viewsets.ViewSet):

    permission_classes = [AllowAny]

    @action(
        detail=False,
        methods=["post"],
        url_path="verify-login-otp"
    )
    def verify_login_otp(self, request):

        serializer = LoginOTPVerifySerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # Consume the OTP before issuing tokens.
        clear_otp(user)

        tokens = generate_jwt_tokens(user)

        return Response(
            {
                "success": True,
                "message": "Login successful.",

                "access": tokens["access"],

                "refresh": tokens["refresh"],

                "must_change_password": (
                    user.must_change_password
                ),

                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# PASSWORD SETUP AND PASSWORD CHANGE
# --------------------------------------------------

class ChangePasswordView(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=["post"],
        url_path="change-password"
    )
    def change_password(self, request):

        user = request.user

        serializer = ChangePasswordSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data[
            "new_password"
        ]

        try:

            validate_password(
                new_password,
                user=user
            )

        except ValidationError as error:

            return Response(
                {
                    "password": error.messages
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)

        user.must_change_password = False

        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "updated_at",
            ]
        )

        # Preserve the Django session if this endpoint is
        # also used by session-authenticated template views.
        if request.auth is None:
            update_session_auth_hash(request, user)

        return Response(
            {
                "success": True,
                "message": "Password updated successfully.",
                "must_change_password": False,
            },
            status=status.HTTP_200_OK
        )


# --------------------------------------------------
# PROFILE
# --------------------------------------------------

class MeView(viewsets.ViewSet):

    permission_classes = [
        IsAuthenticated,
        PasswordSetupComplete,
    ]

    @action(
        detail=False,
        methods=["get"],
        url_path="me"
    )
    def me(self, request):

        return Response({
            "user": UserSerializer(request.user).data,
            "must_change_password": (
                request.user.must_change_password
            ),
        })

    @action(
        detail=False,
        methods=["patch"],
        url_path="update-profile"
    )
    def update_profile(self, request):

        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response({
            "message": "Profile updated successfully.",
            "user": UserSerializer(request.user).data,
        })
