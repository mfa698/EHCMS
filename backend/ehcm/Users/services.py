
import secrets

from datetime import timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone


OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


def generate_otp():
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp):
    return make_password(otp)


def verify_otp(user, submitted_otp):

    if not user.otp_code or not user.otp_created_at:
        return False, "No active OTP. Please log in again."

    expiry = user.otp_created_at + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )

    if timezone.now() >= expiry:
        clear_otp(user)
        return False, "OTP has expired. Please log in again."

    if user.otp_attempts >= MAX_OTP_ATTEMPTS:
        clear_otp(user)
        return False, "Maximum OTP attempts exceeded."

    if not check_password(submitted_otp, user.otp_code):

        user.otp_attempts += 1

        if user.otp_attempts >= MAX_OTP_ATTEMPTS:
            clear_otp(user)
            return False, "Maximum OTP attempts exceeded."

        user.save(update_fields=["otp_attempts"])

        return False, "Incorrect OTP."

    return True, "OTP verified successfully."


def clear_otp(user):

    user.otp_code = ""
    user.otp_created_at = None
    user.otp_attempts = 0

    user.save(
        update_fields=[
            "otp_code",
            "otp_created_at",
            "otp_attempts"
        ]
    )
