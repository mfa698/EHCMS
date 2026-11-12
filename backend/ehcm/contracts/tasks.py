import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from Users.models import User
from notifications.models import Notification
from .models import AppointmentContract, RenewalCase, AuditLog

logger = logging.getLogger(__name__)


def evaluate_contract_expiries():
    today = timezone.localdate()
    contracts = AppointmentContract.objects.select_related(
        "consul__user", "consul__mission__head_of_mission"
    ).filter(
        is_current=True,
        status__in=[
            AppointmentContract.StatusChoices.ACTIVE,
            AppointmentContract.StatusChoices.EXPIRING_SOON,
        ],
    )

    hq_recipients = list(User.objects.filter(role__in=["manager", "officer"], is_active=True))
    alerts_triggered = 0

    for contract in contracts:
        days_left = (contract.end_date - today).days

        if days_left < 0:
            contract.status = AppointmentContract.StatusChoices.EXPIRED
            contract.save(update_fields=["status"])
            continue

        threshold_hit = None
        category = None

        if days_left <= 30 and not contract.alert_30_sent:
            threshold_hit = 30
            category = Notification.CategoryChoices.EXPIRY_30
            contract.alert_30_sent = True
            contract.alert_60_sent = True
            contract.alert_90_sent = True
        elif days_left <= 60 and not contract.alert_60_sent:
            threshold_hit = 60
            category = Notification.CategoryChoices.EXPIRY_60
            contract.alert_60_sent = True
            contract.alert_90_sent = True
        elif days_left <= 90 and not contract.alert_90_sent:
            threshold_hit = 90
            category = Notification.CategoryChoices.EXPIRY_90
            contract.alert_90_sent = True

        if not threshold_hit:
            continue

        with transaction.atomic():
            contract.status = AppointmentContract.StatusChoices.EXPIRING_SOON
            contract.save(
                update_fields=["status", "alert_90_sent", "alert_60_sent", "alert_30_sent"]
            )

            RenewalCase.objects.get_or_create(
                consul=contract.consul,
                expiring_contract=contract,
            )

            recipients = list(hq_recipients)
            if contract.consul.mission.head_of_mission:
                recipients.append(contract.consul.mission.head_of_mission)

            title = f"{threshold_hit}-Day Contract Expiry Alert: {contract.consul.user.full_name}"
            message = (
                f"Appointment contract {contract.reference_number} for {contract.consul.user.full_name} "
                f"({contract.consul.cities_of_operation}) expires on {contract.end_date} ({days_left} days remaining)."
            )

            for recipient in set(recipients):
                email_delivered = False
                try:
                    send_mail(
                        subject=f"[e-HCMS] {title}",
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient.email],
                        fail_silently=False,
                    )
                    email_delivered = True
                except Exception:
                    logger.warning("Failed to send expiry email to %s", recipient.email)

                Notification.objects.create(
                    recipient=recipient,
                    category=category,
                    title=title,
                    message=message,
                    related_entity_type="AppointmentContract",
                    related_entity_id=str(contract.id),
                    email_sent=email_delivered,
                )

            AuditLog.objects.create(
                action=f"EXPIRY_ALERT_{threshold_hit}_DAYS",
                entity_type="AppointmentContract",
                entity_id=str(contract.id),
                after_state={"days_left": days_left, "end_date": str(contract.end_date)},
            )
            alerts_triggered += 1

    return alerts_triggered


@shared_task
def check_contract_expiries():
    count = evaluate_contract_expiries()
    return f"Processed contract expiries; triggered {count} alert(s)."
