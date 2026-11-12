import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Mission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    head_of_mission = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_missions",
        limit_choices_to={"role": "ambassador"},
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contracts_mission"
        ordering = ["country", "name"]

    def __str__(self):
        return f"{self.name} ({self.country})"


class HonoraryConsul(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consul_profile",
        limit_choices_to={"role": "consul"},
    )
    mission = models.ForeignKey(Mission, on_delete=models.PROTECT, related_name="consuls")
    cities_of_operation = models.TextField()
    office_address = models.TextField(blank=True, default="")
    nationality = models.CharField(max_length=100, blank=True, default="")
    date_of_first_appointment = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contracts_honorary_consul"
        ordering = ["user__full_name"]

    def __str__(self):
        return f"{self.user.full_name} — {self.cities_of_operation}"


class AppointmentContract(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRING_SOON = "expiring_soon", "Expiring Soon"
        EXPIRED = "expired", "Expired"
        RENEWED = "renewed", "Renewed (Historical)"
        TERMINATED = "terminated", "Terminated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consul = models.ForeignKey(HonoraryConsul, on_delete=models.CASCADE, related_name="contracts")
    version_number = models.PositiveIntegerField(default=1)
    reference_number = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
        db_index=True,
    )
    is_current = models.BooleanField(default=True, db_index=True)
    alert_90_sent = models.BooleanField(default=False)
    alert_60_sent = models.BooleanField(default=False)
    alert_30_sent = models.BooleanField(default=False)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorized_contracts",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contracts_appointment_contract"
        ordering = ["-version_number", "-start_date"]
        unique_together = ("consul", "version_number")

    @property
    def days_remaining(self):
        return (self.end_date - timezone.localdate()).days

    def __str__(self):
        return f"{self.consul.user.full_name} | v{self.version_number} (Ends {self.end_date})"


class PerformanceEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consul = models.ForeignKey(HonoraryConsul, on_delete=models.CASCADE, related_name="evaluations")
    evaluated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_evaluations",
    )
    period_label = models.CharField(max_length=50)
    rating_score = models.PositiveSmallIntegerField()
    summary = models.TextField()
    strengths = models.TextField(blank=True, default="")
    areas_for_improvement = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contracts_performance_evaluation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Eval: {self.consul.user.full_name} ({self.period_label})"


class Recommendation(models.Model):
    class DecisionChoices(models.TextChoices):
        RENEW = "renew", "Recommend Renewal"
        RENEW_WITH_CONDITIONS = "renew_conditions", "Recommend Renewal with Conditions"
        DO_NOT_RENEW = "do_not_renew", "Do Not Renew"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consul = models.ForeignKey(HonoraryConsul, on_delete=models.CASCADE, related_name="recommendations")
    contract = models.ForeignKey(AppointmentContract, on_delete=models.CASCADE, related_name="recommendations")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hom_recommendations",
    )
    decision = models.CharField(max_length=30, choices=DecisionChoices.choices)
    justification = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contracts_recommendation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_decision_display()} — {self.consul.user.full_name}"


class RenewalCase(models.Model):
    class StatusChoices(models.TextChoices):
        OPEN = "open", "Open / Pending Review"
        UNDER_REVIEW = "under_review", "Under HQ Review"
        APPROVED = "approved", "Approved & Renewed"
        DECLINED = "declined", "Declined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consul = models.ForeignKey(HonoraryConsul, on_delete=models.CASCADE, related_name="renewal_cases")
    expiring_contract = models.OneToOneField(
        AppointmentContract,
        on_delete=models.PROTECT,
        related_name="renewal_case",
    )
    hom_recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renewal_cases",
    )
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_renewals",
    )
    decision_notes = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)
    new_contract = models.OneToOneField(
        AppointmentContract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="originating_renewal",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contracts_renewal_case"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Renewal Case: {self.consul.user.full_name} ({self.status})"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=64)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "contracts_audit_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at}] {self.action} on {self.entity_type} ({self.entity_id})"
