
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import (
    PasswordSetupComplete,
    IsSuperAdmin,
    IsConsul,
    IsAmbassador,
    IsManager,
    IsOfficer
)


class SuperAdminDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        PasswordSetupComplete,
        IsSuperAdmin
    ]

    def get(self, request):

        return Response({
            "message": "Welcome to Super Admin Dashboard",
            "role": request.user.role,
            "full_name": request.user.full_name
        })


class ConsulDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        PasswordSetupComplete,
        IsConsul
    ]

    def get(self, request):

        return Response({
            "message": "Welcome to Consul Dashboard",
            "role": request.user.role,
            "full_name": request.user.full_name
        })


class AmbassadorDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        PasswordSetupComplete,
        IsAmbassador
    ]

    def get(self, request):

        return Response({
            "message": "Welcome to Ambassador Dashboard",
            "role": request.user.role,
            "full_name": request.user.full_name
        })


class ManagerDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        PasswordSetupComplete,
        IsManager
    ]

    def get(self, request):

        return Response({
            "message": "Welcome to Manager Dashboard",
            "role": request.user.role,
            "full_name": request.user.full_name
        })


class OfficerDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        PasswordSetupComplete,
        IsOfficer
    ]

    def get(self, request):

        return Response({
            "message": "Welcome to Officer Dashboard",
            "role": request.user.role,
            "full_name": request.user.full_name
        })
