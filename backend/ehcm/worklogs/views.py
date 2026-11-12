from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from Users.permissions import PasswordSetupComplete
from contracts.models import HonoraryConsul
from .models import WorkLogEntry
from .serializers import WorkLogEntrySerializer

HQ_ROLES = {"manager", "officer", "super_admin"}


class WorkLogEntryViewSet(viewsets.ModelViewSet):
    serializer_class = WorkLogEntrySerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return WorkLogEntry.objects.select_related("consul__user").all()
        if user.role == "ambassador":
            return WorkLogEntry.objects.filter(consul__mission__head_of_mission=user)
        if user.role == "consul":
            return WorkLogEntry.objects.filter(consul__user=user)
        return WorkLogEntry.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != "consul":
            raise PermissionDenied("Only Honorary Consuls can log work entries.")
        consul_profile = HonoraryConsul.objects.filter(user=self.request.user).first()
        if not consul_profile:
            raise ValidationError("No Honorary Consul profile is linked to your user account.")
        serializer.save(consul=consul_profile)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.is_locked:
            raise ValidationError("This work log entry is locked because it was submitted in a quarterly report.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise ValidationError("Locked work log entries cannot be deleted.")
        instance.delete()
