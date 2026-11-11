
from rest_framework.permissions import BasePermission


def _has_completed_password_setup(request):
    setup_token = request.auth and request.auth.get("password_setup", False)
    return (
        request.user.is_authenticated
        and request.user.is_active
        and not request.user.must_change_password
        and not setup_token
    )


class PasswordSetupComplete(BasePermission):

    def has_permission(self, request, view):
        return _has_completed_password_setup(request)


class IsSuperAdmin(BasePermission):

    def has_permission(self, request, view):
        return (
            _has_completed_password_setup(request)
            and request.user.role == "super_admin"
        )


class IsConsul(BasePermission):

    def has_permission(self, request, view):
        return (
            _has_completed_password_setup(request)
            and request.user.role == "consul"
        )


class IsAmbassador(BasePermission):

    def has_permission(self, request, view):
        return (
            _has_completed_password_setup(request)
            and request.user.role == "ambassador"
        )


class IsManager(BasePermission):

    def has_permission(self, request, view):
        return (
            _has_completed_password_setup(request)
            and request.user.role == "manager"
        )


class IsOfficer(BasePermission):

    def has_permission(self, request, view):
        return (
            _has_completed_password_setup(request)
            and request.user.role == "officer"
        )


class IsAuthenticatedAndSetup(BasePermission):

    def has_permission(self, request, view):
        return _has_completed_password_setup(request)


class CanSetPassword(BasePermission):

    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_active:
            return False

        setup_token = request.auth and request.auth.get("password_setup", False)
        if setup_token:
            return request.user.must_change_password

        return not request.user.must_change_password
