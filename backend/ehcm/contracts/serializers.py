from rest_framework import serializers
from .models import (
    Mission,
    HonoraryConsul,
    AppointmentContract,
    PerformanceEvaluation,
    Recommendation,
    RenewalCase,
    AuditLog,
)


class MissionSerializer(serializers.ModelSerializer):
    head_of_mission_name = serializers.CharField(source="head_of_mission.full_name", read_only=True)

    class Meta:
        model = Mission
        fields = [
            "id",
            "name",
            "country",
            "city",
            "head_of_mission",
            "head_of_mission_name",
            "latitude",
            "longitude",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class HonoraryConsulSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    work_id = serializers.CharField(source="user.work_id", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    mission_name = serializers.CharField(source="mission.name", read_only=True)

    class Meta:
        model = HonoraryConsul
        fields = [
            "id",
            "user",
            "work_id",
            "full_name",
            "email",
            "phone_number",
            "mission",
            "mission_name",
            "cities_of_operation",
            "office_address",
            "nationality",
            "date_of_first_appointment",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AppointmentContractSerializer(serializers.ModelSerializer):
    consul_name = serializers.CharField(source="consul.user.full_name", read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = AppointmentContract
        fields = [
            "id",
            "consul",
            "consul_name",
            "version_number",
            "reference_number",
            "start_date",
            "end_date",
            "days_remaining",
            "status",
            "is_current",
            "alert_90_sent",
            "alert_60_sent",
            "alert_30_sent",
            "authorized_by",
            "notes",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "version_number",
            "alert_90_sent",
            "alert_60_sent",
            "alert_30_sent",
            "authorized_by",
            "created_at",
        ]


class PerformanceEvaluationSerializer(serializers.ModelSerializer):
    consul_name = serializers.CharField(source="consul.user.full_name", read_only=True)
    evaluator_name = serializers.CharField(source="evaluated_by.full_name", read_only=True)

    class Meta:
        model = PerformanceEvaluation
        fields = [
            "id",
            "consul",
            "consul_name",
            "evaluated_by",
            "evaluator_name",
            "period_label",
            "rating_score",
            "summary",
            "strengths",
            "areas_for_improvement",
            "created_at",
        ]
        read_only_fields = ["id", "evaluated_by", "created_at"]

    def validate_rating_score(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating score must be between 1 and 5.")
        return value


class RecommendationSerializer(serializers.ModelSerializer):
    consul_name = serializers.CharField(source="consul.user.full_name", read_only=True)
    submitted_by_name = serializers.CharField(source="submitted_by.full_name", read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "consul",
            "consul_name",
            "contract",
            "submitted_by",
            "submitted_by_name",
            "decision",
            "justification",
            "created_at",
        ]
        read_only_fields = ["id", "submitted_by", "created_at"]


class RenewalCaseSerializer(serializers.ModelSerializer):
    consul_name = serializers.CharField(source="consul.user.full_name", read_only=True)
    expiring_reference = serializers.CharField(source="expiring_contract.reference_number", read_only=True)
    expiring_end_date = serializers.DateField(source="expiring_contract.end_date", read_only=True)

    class Meta:
        model = RenewalCase
        fields = [
            "id",
            "consul",
            "consul_name",
            "expiring_contract",
            "expiring_reference",
            "expiring_end_date",
            "hom_recommendation",
            "status",
            "decided_by",
            "decision_notes",
            "decided_at",
            "new_contract",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "decided_by", "decided_at", "new_contract", "created_at", "updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_work_id = serializers.CharField(source="actor.work_id", read_only=True)
    actor_name = serializers.CharField(source="actor.full_name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_work_id",
            "actor_name",
            "action",
            "entity_type",
            "entity_id",
            "before_state",
            "after_state",
            "ip_address",
            "created_at",
        ]
