import secrets
import string

from django import forms
from django.conf import settings
from django.contrib import admin, messages

from .models import User, LoginOTP
from .phone_numbers import normalize_phone_number
from .services.smtp_service import send_temporary_password_email


def generate_temporary_password(length=14):
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(character.islower() for character in password)
            and any(character.isupper() for character in password)
            and any(character.isdigit() for character in password)
            and any(character in "!@#$%" for character in password)
        ):
            return password


class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to automatically generate and email a temporary password for a new user.",
    )

    class Meta:
        model = User
        fields = (
            "work_id",
            "email",
            "full_name",
            "phone_number",
            "role",
            "password",
            "is_active",
            "must_change_password",
            "is_staff",
            "is_superuser",
        )

    def clean_phone_number(self):
        return normalize_phone_number(self.cleaned_data.get("phone_number", ""))

    def clean_password(self):
        raw_password = self.cleaned_data.get("password")
        if not raw_password and not self.instance.pk:
            return generate_temporary_password()
        return raw_password

    def save(self, commit=True):
        user = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            user.set_password(raw_password)
        elif self.instance.pk:
            user.password = User.objects.get(pk=self.instance.pk).password
        if commit:
            user.save()
        return user


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    list_display = ("work_id", "email", "full_name", "role", "is_active", "must_change_password")
    list_filter = ("role", "is_active", "must_change_password", "is_staff")
    search_fields = ("work_id", "email", "full_name", "phone_number")
    ordering = ("work_id",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_active = True
            obj.must_change_password = True

        super().save_model(request, obj, form, change)

        if not change:
            temporary_password = form.cleaned_data["password"]
            login_url = f"{settings.FRONTEND_BASE_URL}/login.html"
            try:
                send_temporary_password_email(
                    recipient=obj.email,
                    full_name=obj.full_name,
                    work_id=obj.work_id,
                    temporary_password=temporary_password,
                    login_url=login_url,
                )
                self.message_user(
                    request,
                    f"Temporary password sent to {obj.email}.",
                    level=messages.SUCCESS,
                )
            except Exception:
                obj.is_active = False
                obj.save(update_fields=["is_active"])
                self.message_user(
                    request,
                    f"User was created but SMTP delivery to {obj.email} failed. The account is inactive.",
                    level=messages.ERROR,
                )


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "is_used", "attempts")
    list_filter = ("is_used",)
