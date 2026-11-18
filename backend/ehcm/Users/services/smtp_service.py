import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_temporary_password_email(*, recipient, full_name, work_id, temporary_password, login_url):
    subject = "Your EHCM account has been created"
    text_content = (
        f"Hello {full_name},\n\n"
        "Your EHCM account has been created.\n\n"
        f"Work ID: {work_id}\n"
        f"Temporary password: {temporary_password}\n\n"
        f"Sign in and set your permanent password: {login_url}\n\n"
        "You will not need SMS verification for this first-time password setup. "
        "SMS verification is required on later logins.\n\n"
        "Please do not share these credentials."
    )
    html_content = (
        "<p>Hello " + str(full_name).replace("&", "&amp;").replace("<", "&lt;") + ",</p>"
        "<p>Your EHCM account has been created.</p>"
        "<p><strong>Work ID:</strong> " + str(work_id) + "<br>"
        "<strong>Temporary password:</strong> " + str(temporary_password) + "</p>"
        "<p><a href=" + '"' + str(login_url) + '"' + ">Sign in and set your permanent password</a></p>"
        "<p>You will not need SMS verification for this first-time password setup. "
        "SMS verification is required on later logins.</p>"
        "<p>Please do not share these credentials.</p>"
    )

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise RuntimeError("SMTP credentials are not configured.")

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_content, "text/html")
    sent = message.send(fail_silently=False)

    if sent != 1:
        raise RuntimeError("SMTP server did not accept the email.")

    logger.info("Temporary-password email sent to %s", recipient)
    return sent
