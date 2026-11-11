
import logging
import africastalking

from django.conf import settings

logger = logging.getLogger(__name__)


def send_otp_sms(phone_number, otp):

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
