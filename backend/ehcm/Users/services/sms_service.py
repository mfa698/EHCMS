import logging
import africastalking
from django.conf import settings

logger = logging.getLogger(__name__)


def send_otp_sms(phone_number: str, otp_code: str) -> bool:
    """
    Sends a 6-digit login OTP via Africa's Talking SMS API.
    In local DEBUG mode without an API key, prints the OTP to the terminal console.
    """
    message = f"Your e-HCMS verification code is: {otp_code}. It expires in 5 minutes."

    if settings.DEBUG and not getattr(settings, "AT_API_KEY", ""):
        print("\n" + "=" * 50)
        print(f"[DEV MODE SMS] To: {phone_number}")
        print(f"[DEV MODE SMS] OTP CODE: {otp_code}")
        print("=" * 50 + "\n")
        return True

    try:
        africastalking.initialize(
            username=settings.AT_USERNAME,
            api_key=settings.AT_API_KEY,
        )
        sms = africastalking.SMS
        response = sms.send(message, [phone_number])
        logger.info("Africa's Talking SMS response: %s", response)
        return True
    except Exception as exc:
        logger.error("Failed to send OTP SMS to %s: %s", phone_number, exc)
        return False
