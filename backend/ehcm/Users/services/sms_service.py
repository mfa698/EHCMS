
import logging
import africastalking

from django.conf import settings
from django.core.exceptions import ValidationError

from ..phone_numbers import normalize_phone_number

logger = logging.getLogger(__name__)


def send_otp_sms(phone_number, otp):

    try:
        phone_number = normalize_phone_number(phone_number)
    except ValidationError:
        logger.exception("Cannot send OTP to an invalid phone number.")
        raise

    username = settings.AT_USERNAME
    api_key = settings.AT_API_KEY

    africastalking.initialize(username, api_key)

    sms = africastalking.SMS

    message = (
        f"Your EHCM login verification code is {otp}. "
        "It expires in 5 minutes. Do not share this code."
    )

    try:
        response = sms.send(
            message,
            [phone_number]
        )

        logger.info("OTP SMS submitted successfully.")

        return response

    except Exception:
        logger.exception("Failed to send OTP SMS.")
        raise
