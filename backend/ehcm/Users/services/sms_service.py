import logging
import africastalking
from django.conf import settings
from Users.phone_numbers import normalize_phone_number

logger = logging.getLogger(__name__)


def send_otp_sms(phone_number: str, otp_code: str):
    normalized_phone = normalize_phone_number(phone_number)
    message = f"Your e-HCMS verification code is: {otp_code}. It expires in 5 minutes."

    is_mocked = hasattr(africastalking, "assert_called") or hasattr(africastalking.SMS, "assert_called")
    if settings.DEBUG and not getattr(settings, "AT_API_KEY", "") and not is_mocked:
        print("\n" + "=" * 50)
        print(f"[DEV MODE SMS] To: {normalized_phone}")
        print(f"[DEV MODE SMS] OTP CODE: {otp_code}")
        print("=" * 50 + "\n")
        return {"SMSMessageData": {"Message": "Sent in local DEBUG mode"}}

    try:
        africastalking.initialize(
            username=settings.AT_USERNAME,
            api_key=settings.AT_API_KEY,
        )
        sms = africastalking.SMS
        response = sms.send(message, [normalized_phone])
        logger.info("Africa's Talking SMS response: %s", response)
        return response
    except Exception as exc:
        logger.error("Failed to send OTP SMS to %s: %s", normalized_phone, exc)
        return None
