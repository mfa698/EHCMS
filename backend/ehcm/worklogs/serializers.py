from rest_framework import serializers
from .models import WorkLogEntry


class WorkLogEntrySerializer(serializers.ModelSerializer):
    consul_name = serializers.CharField(source="consul.user.full_name", read_only=True)

    class Meta:
        model = WorkLogEntry
        fields = [
            "id",
            "consul",
            "consul_name",
            "activity_date",
            "category",
            "title",
            "description",
            "location",
            "stakeholders",
            "outcomes",
            "status",
            "is_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "consul", "status", "is_locked", "created_at", "updated_at"]
