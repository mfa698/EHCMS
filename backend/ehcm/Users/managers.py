
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):

    def create_user(
        self,
        email,
        work_id,
        full_name,
        phone_number,
        role,
        password=None,
        **extra_fields
    ):

        if not email:
            raise ValueError("Email is required.")

        if not work_id:
            raise ValueError("Work ID is required.")

        if not password:
            raise ValueError("Password is required.")

        email = self.normalize_email(email).lower()

        user = self.model(
            email=email,
            work_id=work_id,
            full_name=full_name,
            phone_number=phone_number,
            role=role,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email,
        work_id,
        full_name,
        phone_number,
        password,
        **extra_fields
    ):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("must_change_password", False)

        return self.create_user(
            email=email,
            work_id=work_id,
            full_name=full_name,
            phone_number=phone_number,
            role="super_admin",
            password=password,
            **extra_fields
        )
