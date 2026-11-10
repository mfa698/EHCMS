
import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "id",
            "work_id",
            "full_name",
            "email",
            "phone_number",
            "role",
            "is_active",
            "must_change_password",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "is_active",
            "must_change_password",
            "created_at",
        ]


class AdminCreateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "full_name",
            "work_id",
            "email",
            "phone_number",
            "role",
        ]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email is already registered."
            )

        return value

    def validate_work_id(self, value):
        value = value.strip().upper()

        if User.objects.filter(work_id__iexact=value).exists():
            raise serializers.ValidationError(
                "This Work ID is already registered."
            )

        return value

    def validate_phone_number(self, value):
        value = re.sub(r"[\s()-]", "", value)

        if value.startswith("0"):
            value = "+254" + value[1:]
        elif value.startswith("254"):
            value = "+" + value

        if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
            raise serializers.ValidationError(
                "Enter a valid international phone number."
            )

        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "This phone number is already registered."
            )

        return value

    def validate_role(self, value):

        if value == User.RoleChoices.SUPER_ADMIN:
            raise serializers.ValidationError(
                "Super Admin accounts cannot be created through this endpoint."
            )

        return value


class ChangePasswordSerializer(serializers.Serializer):

    current_password = serializers.CharField(
        write_only=True
    )

    new_password = serializers.CharField(
        write_only=True
    )

    confirm_password = serializers.CharField(
        write_only=True
    )

    def validate(self, data):

        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        try:
            validate_password(
                data["new_password"],
                self.context["request"].user
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "new_password": error.messages
            })

        return data
