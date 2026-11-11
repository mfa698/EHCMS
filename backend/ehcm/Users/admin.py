
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError

from .models import User, LoginOTP
from .phone_numbers import normalize_phone_number


class UserAdminForm(forms.ModelForm):

    password = forms.CharField(
        label="Temporary password",
        widget=forms.PasswordInput,
        strip=False,
        required=False,
    )

    class Meta:
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_password = self.instance.password
        if self.instance._state.adding:
            self.fields["password"].required = True
        else:
            self.fields["password"].help_text = (
                "Leave blank to keep the current password. "
                "Enter a new temporary password to reset it."
            )

    def save(self, commit=True):
        is_new = self.instance._state.adding
        user = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")

        if raw_password:
            user.set_password(raw_password)
        elif not is_new:
            user.password = self._initial_password

        if commit:
            user.save()
            self.save_m2m()

        return user

    def clean_phone_number(self):
        try:
            return normalize_phone_number(
                self.cleaned_data["phone_number"]
            )
        except ValidationError as error:
            raise forms.ValidationError(error.messages)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    form = UserAdminForm

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
