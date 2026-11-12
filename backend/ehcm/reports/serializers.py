from rest_framework import serializers
from .models import QuarterlyReport, ReportAttachment


class ReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAttachment
        fields = [
            "id",
            "report",
            "file",
            "original_filename",
            "file_size_bytes",
            "mime_type",
            "uploaded_by",
            "uploaded_at",
        ]
        read_only_fields = ["id", "original_filename", "file_size_bytes", "mime_type", "uploaded_by", "uploaded_at"]


class QuarterlyReportSerializer(serializers.ModelSerializer):
    consul_name = serializers.CharField(source="consul.user.full_name", read_only=True)
    mission_name = serializers.CharField(source="consul.mission.name", read_only=True)
    attachments = ReportAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = QuarterlyReport
        fields = [
            "id",
            "consul",
            "consul_name",
            "mission_name",
            "year",
            "quarter",
            "version",
            "receipt_number",
            "executive_summary",
            "trade_and_investment",
            "diaspora_and_consular_services",
            "cultural_and_public_diplomacy",
            "challenges_and_recommendations",
            "planned_next_quarter",
            "linked_work_logs",
            "status",
            "submitted_at",
            "hom_remarks",
            "reviewed_by",
            "reviewed_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "consul",
            "version",
            "receipt_number",
            "status",
            "submitted_at",
            "hom_remarks",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
