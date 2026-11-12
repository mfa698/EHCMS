from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from Users.permissions import PasswordSetupComplete
from notifications.models import Notification
from .models import (
    Mission,
    HonoraryConsul,
    AppointmentContract,
    PerformanceEvaluation,
    Recommendation,
    RenewalCase,
    AuditLog,
)
from .serializers import (
    MissionSerializer,
    HonoraryConsulSerializer,
    AppointmentContractSerializer,
    PerformanceEvaluationSerializer,
    RecommendationSerializer,
    RenewalCaseSerializer,
    AuditLogSerializer,
)

HQ_ROLES = {"manager", "officer", "super_admin"}


def log_audit(request, action_name, entity_type, entity_id, before_state=None, after_state=None):
    ip = request.META.get("REMOTE_ADDR") if request else None
    actor = request.user if (request and request.user.is_authenticated) else None
    AuditLog.objects.create(
        actor=actor,
        action=action_name,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_state=before_state,
        after_state=after_state,
        ip_address=ip,
    )


class MissionViewSet(viewsets.ModelViewSet):
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return Mission.objects.all()
        if user.role == "ambassador":
            return Mission.objects.filter(head_of_mission=user)
        if user.role == "consul":
            return Mission.objects.filter(consuls__user=user)
        return Mission.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role not in HQ_ROLES:
            raise PermissionDenied("Only HQ staff can create or assign missions.")
        mission = serializer.save()
        log_audit(self.request, "MISSION_CREATED", "Mission", mission.id, after_state={"name": mission.name})


class HonoraryConsulViewSet(viewsets.ModelViewSet):
    serializer_class = HonoraryConsulSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return HonoraryConsul.objects.select_related("user", "mission").all()
        if user.role == "ambassador":
            return HonoraryConsul.objects.select_related("user", "mission").filter(mission__head_of_mission=user)
        if user.role == "consul":
            return HonoraryConsul.objects.select_related("user", "mission").filter(user=user)
        return HonoraryConsul.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role not in HQ_ROLES:
            raise PermissionDenied("Only HQ staff can register Honorary Consul profiles.")
        profile = serializer.save()
        log_audit(
            self.request,
            "CONSUL_PROFILE_CREATED",
            "HonoraryConsul",
            profile.id,
            after_state={"user": profile.user.work_id, "mission": profile.mission.name},
        )


class AppointmentContractViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentContractSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return AppointmentContract.objects.select_related("consul__user", "consul__mission").all()
        if user.role == "ambassador":
            return AppointmentContract.objects.filter(consul__mission__head_of_mission=user)
        if user.role == "consul":
            return AppointmentContract.objects.filter(consul__user=user)
        return AppointmentContract.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role not in HQ_ROLES:
            raise PermissionDenied("Only HQ staff can issue appointment contracts.")
        consul = serializer.validated_data["consul"]
        AppointmentContract.objects.filter(consul=consul, is_current=True).update(is_current=False)
        latest = AppointmentContract.objects.filter(consul=consul).order_by("-version_number").first()
        next_version = (latest.version_number + 1) if latest else 1
        contract = serializer.save(
            version_number=next_version,
            is_current=True,
            authorized_by=self.request.user,
        )
        log_audit(
            self.request,
            "CONTRACT_ISSUED",
            "AppointmentContract",
            contract.id,
            after_state={"reference": contract.reference_number, "version": next_version},
        )

class PerformanceEvaluationViewSet(viewsets.ModelViewSet):
    serializer_class = PerformanceEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return PerformanceEvaluation.objects.all()
        if user.role == "ambassador":
            return PerformanceEvaluation.objects.filter(consul__mission__head_of_mission=user)
        if user.role == "consul":
            return PerformanceEvaluation.objects.filter(consul__user=user)
        return PerformanceEvaluation.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in {"ambassador", "manager", "super_admin"}:
            raise PermissionDenied("Only a Head of Mission or HQ Manager can submit performance evaluations.")
        consul = serializer.validated_data["consul"]
        if user.role == "ambassador" and consul.mission.head_of_mission != user:
            raise PermissionDenied("You can only evaluate Honorary Consuls under your assigned Mission.")
        evaluation = serializer.save(evaluated_by=user)
        log_audit(
            self.request,
            "EVALUATION_SUBMITTED",
            "PerformanceEvaluation",
            evaluation.id,
            after_state={"consul": consul.user.work_id, "score": evaluation.rating_score},
        )


class RecommendationViewSet(viewsets.ModelViewSet):
    serializer_class = RecommendationSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return Recommendation.objects.all()
        if user.role == "ambassador":
            return Recommendation.objects.filter(consul__mission__head_of_mission=user)
        return Recommendation.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "ambassador":
            raise PermissionDenied("Only a Head of Mission (Ambassador) can submit renewal recommendations.")
        consul = serializer.validated_data["consul"]
        if consul.mission.head_of_mission != user:
            raise PermissionDenied("This Honorary Consul is not assigned to your Mission.")
        contract = serializer.validated_data["contract"]
        rec = serializer.save(submitted_by=user)

        renewal_case, _ = RenewalCase.objects.get_or_create(
            consul=consul,
            expiring_contract=contract,
        )
        renewal_case.hom_recommendation = rec
        renewal_case.status = RenewalCase.StatusChoices.UNDER_REVIEW
        renewal_case.save(update_fields=["hom_recommendation", "status", "updated_at"])

        log_audit(
            self.request,
            "HOM_RECOMMENDATION_SUBMITTED",
            "Recommendation",
            rec.id,
            after_state={"decision": rec.decision, "contract": contract.reference_number},
        )


class RenewalCaseViewSet(viewsets.ModelViewSet):
    serializer_class = RenewalCaseSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return RenewalCase.objects.select_related("consul__user", "expiring_contract").all()
        if user.role == "ambassador":
            return RenewalCase.objects.filter(consul__mission__head_of_mission=user)
        return RenewalCase.objects.none()

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_renewal(self, request, pk=None):
        _ = pk
        if request.user.role not in {"manager", "super_admin"}:
            raise PermissionDenied("Only HQ Directors/Managers can approve contract renewals.")

        renewal_case = self.get_object()
        if renewal_case.status == RenewalCase.StatusChoices.APPROVED:
            raise ValidationError("This renewal case has already been approved.")

        new_reference = request.data.get("reference_number")
        new_start_date = request.data.get("start_date")
        new_end_date = request.data.get("end_date")
        notes = request.data.get("decision_notes", "")

        if not all([new_reference, new_start_date, new_end_date]):
            raise ValidationError("reference_number, start_date, and end_date are required to issue a renewed contract.")

        with transaction.atomic():
            old_contract = renewal_case.expiring_contract
            before_state = {"contract_id": str(old_contract.id), "status": old_contract.status}

            old_contract.status = AppointmentContract.StatusChoices.RENEWED
            old_contract.is_current = False
            old_contract.save(update_fields=["status", "is_current"])

            new_contract = AppointmentContract.objects.create(
                consul=renewal_case.consul,
                version_number=old_contract.version_number + 1,
                reference_number=new_reference,
                start_date=new_start_date,
                end_date=new_end_date,
                status=AppointmentContract.StatusChoices.ACTIVE,
                is_current=True,
                authorized_by=request.user,
                notes=notes,
            )

            renewal_case.status = RenewalCase.StatusChoices.APPROVED
            renewal_case.decided_by = request.user
            renewal_case.decision_notes = notes
            renewal_case.decided_at = timezone.now()
            renewal_case.new_contract = new_contract
            renewal_case.save()

            Notification.objects.create(
                recipient=renewal_case.consul.user,
                category=Notification.CategoryChoices.RENEWAL_DECISION,
                title="Appointment Contract Renewed",
                message=f"Your appointment has been renewed under reference {new_reference} through {new_end_date}.",
                related_entity_type="AppointmentContract",
                related_entity_id=str(new_contract.id),
            )

            log_audit(
                request,
                "CONTRACT_RENEWED",
                "RenewalCase",
                renewal_case.id,
                before_state=before_state,
                after_state={"new_contract_id": str(new_contract.id), "version": new_contract.version_number},
            )

        return Response(RenewalCaseSerializer(renewal_case).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="decline")
    def decline_renewal(self, request, pk=None):
        _ = pk
        if request.user.role not in {"manager", "super_admin"}:
            raise PermissionDenied("Only HQ Directors/Managers can decline contract renewals.")

        renewal_case = self.get_object()
        notes = request.data.get("decision_notes", "")

        with transaction.atomic():
            renewal_case.status = RenewalCase.StatusChoices.DECLINED
            renewal_case.decided_by = request.user
            renewal_case.decision_notes = notes
            renewal_case.decided_at = timezone.now()
            renewal_case.save()

            log_audit(
                request,
                "CONTRACT_RENEWAL_DECLINED",
                "RenewalCase",
                renewal_case.id,
                after_state={"status": "declined", "notes": notes},
            )

        return Response(RenewalCaseSerializer(renewal_case).data, status=status.HTTP_200_OK)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        if self.request.user.role in {"manager", "super_admin"}:
            return AuditLog.objects.select_related("actor").all()
        return AuditLog.objects.none()
