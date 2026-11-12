from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "category",
            "title",
            "message",
            "related_entity_type",
            "related_entity_id",
            "is_read",
            "email_sent",
            "created_at",
        ]
        read_only_fields = fields
