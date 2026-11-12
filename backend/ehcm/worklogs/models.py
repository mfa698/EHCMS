import uuid
from django.core.exceptions import ValidationError
from django.db import models
from contracts.models import HonoraryConsul


class WorkLogEntry(models.Model):
    class ActivityCategory(models.TextChoices):
        TRADE_INVESTMENT = "trade_investment", "Trade & Investment Promotion"
        DIASPORA_WELFARE = "diaspora_welfare", "Diaspora Welfare & Consular Assistance"
        CULTURAL_DIPLOMACY = "cultural_diplomacy", "Cultural & Public Diplomacy"
        GOVERNMENT_LIAISON = "government_liaison", "Host Government & Institutional Liaison"
        TOURISM_PROMOTION = "tourism_promotion", "Tourism Promotion"
        OTHER = "other", "Other Official Activity"

    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Draft"
        INCLUDED = "included", "Included in Report"
        LOCKED = "locked", "Locked (Submitted)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consul = models.ForeignKey(HonoraryConsul, on_delete=models.CASCADE, related_name="work_logs")
    activity_date = models.DateField(db_index=True)
    category = models.CharField(max_length=30, choices=ActivityCategory.choices, default=ActivityCategory.OTHER)
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=150, blank=True, default="")
    stakeholders = models.TextField(blank=True, default="")
    outcomes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.DRAFT, db_index=True)
    is_locked = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "worklogs_work_log_entry"
        ordering = ["-activity_date", "-created_at"]

    def save(self, *args, **kwargs):
        if self.pk:
            existing = WorkLogEntry.objects.filter(pk=self.pk).first()
            if existing and existing.is_locked:
                raise ValidationError("Locked work log entries cannot be modified.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.activity_date} — {self.title}"
