import uuid
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class CategoryChoices(models.TextChoices):
        EXPIRY_90 = "expiry_90", "Contract Expiry (90 Days)"
        EXPIRY_60 = "expiry_60", "Contract Expiry (60 Days)"
        EXPIRY_30 = "expiry_30", "Contract Expiry (30 Days)"
        REPORT_SUBMITTED = "report_submitted", "Quarterly Report Submitted"
        RENEWAL_DECISION = "renewal_decision", "Contract Renewal Decision"
        SYSTEM = "system", "System Notification"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    category = models.CharField(max_length=30, choices=CategoryChoices.choices, default=CategoryChoices.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_entity_type = models.CharField(max_length=50, blank=True, default="")
    related_entity_id = models.CharField(max_length=64, blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient.work_id}: {self.title}"
