from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, LoginOTP


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("work_id", "email", "full_name", "role", "is_active", "must_change_password")
    list_filter = ("role", "is_active", "must_change_password", "is_staff")
    search_fields = ("work_id", "email", "full_name", "phone_number")
    ordering = ("work_id",)

    fieldsets = (
        (None, {"fields": ("work_id", "email", "password")}),
        ("Personal Info", {"fields": ("full_name", "phone_number")}),
        ("Role & Status", {"fields": ("role", "is_active", "must_change_password", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "work_id",
                    "email",
                    "full_name",
                    "phone_number",
                    "role",
                    "password1",
                    "password2",
                    "is_active",
                    "must_change_password",
                ),
            },
        ),
    )


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "is_used", "attempts")
    list_filter = ("is_used",)
