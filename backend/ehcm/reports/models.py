import os
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from contracts.models import HonoraryConsul
from worklogs.models import WorkLogEntry


def report_attachment_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"reports/{instance.report.year}/Q{instance.report.quarter}/{instance.report.id}/{uuid.uuid4()}{ext}"


def validate_file_size(value):
    if value.size > 10 * 1024 * 1024:
        raise ValidationError("File size must not exceed 10 MB.")


class QuarterlyReport(models.Model):
    class QuarterChoices(models.IntegerChoices):
        Q1 = 1, "Q1 (Jan–Mar)"
        Q2 = 2, "Q2 (Apr–Jun)"
        Q3 = 3, "Q3 (Jul–Sep)"
        Q4 = 4, "Q4 (Oct–Dec)"

    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under HoM Review"
        ENDORSED = "endorsed", "Endorsed by HoM"
        REVISION_REQUESTED = "revision_requested", "Revision Requested"
        ARCHIVED = "archived", "Archived (HQ)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consul = models.ForeignKey(HonoraryConsul, on_delete=models.CASCADE, related_name="quarterly_reports")
    year = models.PositiveIntegerField(db_index=True)
    quarter = models.PositiveSmallIntegerField(choices=QuarterChoices.choices, db_index=True)
    version = models.PositiveIntegerField(default=1)
    receipt_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    executive_summary = models.TextField(blank=True, default="")
    trade_and_investment = models.TextField(blank=True, default="")
    diaspora_and_consular_services = models.TextField(blank=True, default="")
    cultural_and_public_diplomacy = models.TextField(blank=True, default="")
    challenges_and_recommendations = models.TextField(blank=True, default="")
    planned_next_quarter = models.TextField(blank=True, default="")

    linked_work_logs = models.ManyToManyField(WorkLogEntry, blank=True, related_name="quarterly_reports")
    status = models.CharField(max_length=25, choices=StatusChoices.choices, default=StatusChoices.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    hom_remarks = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_reports"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reports_quarterly_report"
        ordering = ["-year", "-quarter", "-version"]
        unique_together = ("consul", "year", "quarter", "version")

    def submit_report(self):
        if self.status not in [self.StatusChoices.DRAFT, self.StatusChoices.REVISION_REQUESTED]:
            raise ValidationError("Only draft or revision-requested reports can be submitted.")

        if not self.receipt_number:
            short_id = str(self.id).split("-")[0].upper()
            self.receipt_number = f"EHCMS-{self.year}Q{self.quarter}-{short_id}"

        self.status = self.StatusChoices.SUBMITTED
        self.submitted_at = timezone.now()
        self.save()

        self.linked_work_logs.filter(is_locked=False).update(
            is_locked=True,
            status=WorkLogEntry.StatusChoices.LOCKED,
        )

    def __str__(self):
        return f"{self.consul.user.full_name} — {self.year} Q{self.quarter} (v{self.version})"


class ReportAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(QuarterlyReport, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=report_attachment_path,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"]),
            validate_file_size,
        ],
    )
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="uploaded_attachments"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports_report_attachment"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.report})"
