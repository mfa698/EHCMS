
from django.contrib import admin

from .models import User, LoginOTP


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = (
        "work_id",
        "full_name",
        "email",
        "role",
        "is_active",
        "must_change_password",
        "created_at",
    )

    list_filter = (
        "role",
        "is_active",
        "must_change_password",
    )

    search_fields = (
        "work_id",
        "full_name",
        "email",
        "phone_number",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_login",
    )


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "attempts",
        "expires_at",
        "is_used",
        "created_at",
    )

    readonly_fields = (
        "id",
        "otp_hash",
        "created_at",
    )
