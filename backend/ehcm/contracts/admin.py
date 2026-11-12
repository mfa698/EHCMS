from django.contrib import admin
from .models import (
    Mission,
    HonoraryConsul,
    AppointmentContract,
    PerformanceEvaluation,
    Recommendation,
    RenewalCase,
    AuditLog,
)


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "city", "head_of_mission", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name", "country", "city")


@admin.register(HonoraryConsul)
class HonoraryConsulAdmin(admin.ModelAdmin):
    list_display = ("user", "mission", "cities_of_operation", "date_of_first_appointment", "is_active")
    list_filter = ("mission", "is_active")
    search_fields = ("user__full_name", "user__work_id", "cities_of_operation")


@admin.register(AppointmentContract)
class AppointmentContractAdmin(admin.ModelAdmin):
    list_display = ("consul", "version_number", "reference_number", "start_date", "end_date", "status", "is_current")
    list_filter = ("status", "is_current", "alert_90_sent", "alert_60_sent", "alert_30_sent")
    search_fields = ("consul__user__full_name", "reference_number")


@admin.register(PerformanceEvaluation)
class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = ("consul", "period_label", "rating_score", "evaluated_by", "created_at")
    list_filter = ("period_label", "rating_score")


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("consul", "contract", "decision", "submitted_by", "created_at")
    list_filter = ("decision",)


@admin.register(RenewalCase)
class RenewalCaseAdmin(admin.ModelAdmin):
    list_display = ("consul", "expiring_contract", "status", "decided_by", "decided_at")
    list_filter = ("status",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "entity_type", "entity_id", "actor")
    list_filter = ("action", "entity_type")
    readonly_fields = ("id", "actor", "action", "entity_type", "entity_id", "before_state", "after_state", "ip_address", "created_at")
