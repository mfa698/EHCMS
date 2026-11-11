# It handles:

# Work ID and password authentication.

# OTP generation.

# OTP SMS delivery.

# OTP expiration.

# OTP attempt restrictions.

# JWT generation after successful OTP verification.


import secrets
import logging

from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from rest_framework.throttling import AnonRateThrottle

from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import User, LoginOTP
from .services.sms_service import send_otp_sms


logger = logging.getLogger(__name__)


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class OTPThrottle(AnonRateThrottle):
    scope = "otp"


class LoginView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):

        work_id = request.data.get("work_id", "").strip().upper()
        password = request.data.get("password", "")

        if not work_id or not password:
            return Response(
                {"error": "Work ID and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_record = User.objects.filter(
            work_id__iexact=work_id
        ).first()

        if not user_record:
            return Response(
                {"error": "Invalid Work ID or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Django's default authentication backend uses email
        # because email is the USERNAME_FIELD.
        user = authenticate(
            request,
            username=user_record.email,
            password=password
        )

        if not user or not user.is_active:
            return Response(
                {"error": "Invalid Work ID or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.must_change_password:
            setup_token = AccessToken.for_user(user)
            setup_token["password_setup"] = True

            return Response(
                {
                    "message": "Set your permanent password to continue.",
                    "requires_password_change": True,
                    "access": str(setup_token),
                    "user": {
                        "id": str(user.id),
                        "work_id": user.work_id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "role": user.role,
                        "must_change_password": True,
                    }
                },
                status=status.HTTP_200_OK
            )

        otp = f"{secrets.randbelow(1000000):06d}"

        expires_at = timezone.now() + timedelta(minutes=5)

        # Invalidate outstanding OTPs for this user.
        LoginOTP.objects.filter(
            user=user,
            is_used=False
        ).update(is_used=True)

        challenge = LoginOTP.objects.create(
            user=user,
            otp_hash=make_password(otp),
            expires_at=expires_at
        )

        try:
            send_otp_sms(user.phone_number, otp)

        except Exception:
            challenge.delete()

            logger.exception(
                "OTP delivery failed for user %s",
                user.work_id
            )

            return Response(
                {
                    "error": "OTP delivery failed. Please try again."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {
                "message": "OTP sent to your registered phone.",
                "challenge_id": str(challenge.id),
                "requires_otp": True,
                "phone_number": (
                    "*" * max(0, len(user.phone_number) - 4)
                    + user.phone_number[-4:]
                )
            },
            status=status.HTTP_200_OK
        )


class VerifyLoginOTPView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPThrottle]

    def post(self, request):

        challenge_id = request.data.get("challenge_id", "")
        otp_code = request.data.get("otp_code", "")

        if not challenge_id or not otp_code:
            return Response(
                {"error": "Challenge ID and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            challenge = LoginOTP.objects.select_for_update().filter(
                id=challenge_id,
                is_used=False
            ).first()

            if not challenge:
                return Response(
                    {"error": "Invalid or expired OTP."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not challenge.user.is_active:
                challenge.is_used = True
                challenge.save(update_fields=["is_used"])

                return Response(
                    {"error": "Account is inactive."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if timezone.now() > challenge.expires_at:
                challenge.is_used = True
                challenge.save(update_fields=["is_used"])

                return Response(
                    {"error": "OTP has expired. Please login again."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if challenge.attempts >= 5:
                challenge.is_used = True
                challenge.save(update_fields=["is_used"])

                return Response(
                    {"error": "Too many attempts. Please login again."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            if not check_password(otp_code, challenge.otp_hash):

                challenge.attempts += 1

                if challenge.attempts >= 5:
                    challenge.is_used = True

                challenge.save(
                    update_fields=["attempts", "is_used"]
                )

                return Response(
                    {"error": "Incorrect OTP."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            challenge.is_used = True
            challenge.save(update_fields=["is_used"])

            user = challenge.user

            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "message": "Login successful.",

                    "access": str(refresh.access_token),

                    "refresh": str(refresh),

                    "user": {
                        "id": str(user.id),
                        "work_id": user.work_id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "phone_number": user.phone_number,
                        "role": user.role,
                        "must_change_password": user.must_change_password,
                    }
                },
                status=status.HTTP_200_OK
            )
