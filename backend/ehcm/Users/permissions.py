
from rest_framework.permissions import BasePermission


class PasswordSetupComplete(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and not request.user.must_change_password
        )


class IsSuperAdmin(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "super_admin"
        )


class IsConsul(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "consul"
        )


class IsAmbassador(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "ambassador"
        )


class IsManager(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "manager"
        )


class IsOfficer(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "officer"
        )


class IsAuthenticatedAndSetup(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.is_active
            and not request.user.must_change_password
        )
