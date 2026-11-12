from django import forms
from django.contrib import admin
from .models import User, LoginOTP
from .phone_numbers import normalize_phone_number


class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to keep the current password when editing.",
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
            raise forms.ValidationError("Password is required when creating a new user.")
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


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "is_used", "attempts")
    list_filter = ("is_used",)
