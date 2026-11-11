
import uuid

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MinLengthValidator

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):

    class RoleChoices(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        CONSUL = "consul", "Consul"
        AMBASSADOR = "ambassador", "Ambassador"
        MANAGER = "manager", "Manager"
        OFFICER = "officer", "Officer"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    email = models.EmailField(
        unique=True,
        max_length=254
    )

    work_id = models.CharField(
        max_length=30,
        unique=True
    )

    full_name = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(2)]
    )

    phone_number = models.CharField(
        max_length=20,
        unique=True
    )

    role = models.CharField(
        max_length=30,
        choices=RoleChoices.choices,
        default=RoleChoices.OFFICER
    )

    must_change_password = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "work_id",
        "full_name",
        "phone_number"
    ]

    class Meta:
        db_table = "users_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["work_id"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.work_id})"


class LoginOTP(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="login_otps"
    )

    otp_hash = models.CharField(max_length=128)

    attempts = models.PositiveSmallIntegerField(default=0)

    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_login_otp"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user.work_id}"
