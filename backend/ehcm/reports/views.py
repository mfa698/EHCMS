from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions, parsers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from Users.models import User
from Users.permissions import PasswordSetupComplete
from contracts.models import HonoraryConsul
from contracts.views import log_audit
from notifications.models import Notification
from .models import QuarterlyReport, ReportAttachment
from .serializers import QuarterlyReportSerializer, ReportAttachmentSerializer

HQ_ROLES = {"manager", "officer", "super_admin"}


class QuarterlyReportViewSet(viewsets.ModelViewSet):
    serializer_class = QuarterlyReportSerializer
    permission_classes = [permissions.IsAuthenticated, PasswordSetupComplete]

    def get_queryset(self):
        user = self.request.user
        if user.role in HQ_ROLES:
            return QuarterlyReport.objects.select_related("consul__user", "consul__mission").all()
        if user.role == "ambassador":
            return QuarterlyReport.objects.filter(consul__mission__head_of_mission=user)
        if user.role == "consul":
            return QuarterlyReport.objects.filter(consul__user=user)
        return QuarterlyReport.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != "consul":
            raise PermissionDenied("Only Honorary Consuls can create quarterly reports.")
        consul_profile = HonoraryConsul.objects.filter(user=self.request.user).first()
        if not consul_profile:
            raise ValidationError("No Honorary Consul profile is linked to your account.")
        serializer.save(consul=consul_profile)

    def perform_update(self, serializer):
        report = self.get_object()
        if report.status not in [
            QuarterlyReport.StatusChoices.DRAFT,
            QuarterlyReport.StatusChoices.REVISION_REQUESTED,
        ]:
            raise ValidationError("Submitted or endorsed reports cannot be edited directly.")
        serializer.save()

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        report = self.get_object()
        if request.user.role != "consul" or report.consul.user != request.user:
            raise PermissionDenied("Only the owning Honorary Consul can submit this report.")

        with transaction.atomic():
            report.submit_report()

            # Notify assigned Head of Mission and HQ Officers
            recipients = list(User.objects.filter(role__in=["manager", "officer"], is_active=True))
            if report.consul.mission.head_of_mission:
                recipients.append(report.consul.mission.head_of_mission)

            for recipient in set(recipients):
                Notification.objects.create(
                    recipient=recipient,
                    category=Notification.CategoryChoices.REPORT_SUBMITTED,
                    title=f"Quarterly Report Submitted: {report.consul.user.full_name} ({report.year} Q{report.quarter})",
                    message=f"Receipt {report.receipt_number} issued on {report.submitted_at:%Y-%m-%d %H:%M}.",
                    related_entity_type="QuarterlyReport",
                    related_entity_id=str(report.id),
                )

            log_audit(
                request,
                "REPORT_SUBMITTED",
                "QuarterlyReport",
                report.id,
                after_state={"receipt_number": report.receipt_number, "status": report.status},
            )

        return Response(QuarterlyReportSerializer(report).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        """
        Head of Mission (Ambassador) review action: 'endorse' or 'request_revision'.
        """
        report = self.get_object()
        if request.user.role != "ambassador" or report.consul.mission.head_of_mission != request.user:
            raise PermissionDenied("Only the supervising Head of Mission can review this report.")

        decision = request.data.get("decision")
        remarks = request.data.get("hom_remarks", "")

        if decision not in {"endorse", "request_revision"}:
            raise ValidationError("decision must be either 'endorse' or 'request_revision'.")

        with transaction.atomic():
            if decision == "endorse":
                report.status = QuarterlyReport.StatusChoices.ENDORSED
            else:
                report.status = QuarterlyReport.StatusChoices.REVISION_REQUESTED

            report.hom_remarks = remarks
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()

            Notification.objects.create(
                recipient=report.consul.user,
                category=Notification.CategoryChoices.SYSTEM,
                title=f"Quarterly Report {report.get_status_display()}",
                message=f"Your {report.year} Q{report.quarter} report was reviewed by {request.user.full_name}. Remarks: {remarks}",
                related_entity_type="QuarterlyReport",
                related_entity_id=str(report.id),
            )

            log_audit(
                request,
                f"REPORT_{decision.upper()}",
                "QuarterlyReport",
                report.id,
                after_state={"status": report.status, "remarks": remarks},
            )

        return Response(QuarterlyReportSerializer(report).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="attachments",
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def upload_attachment(self, request, pk=None):
        report = self.get_object()
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            raise ValidationError("No file provided.")

        attachment = ReportAttachment.objects.create(
            report=report,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size_bytes=uploaded_file.size,
            mime_type=getattr(uploaded_file, "content_type", ""),
            uploaded_by=request.user,
        )
        return Response(ReportAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)
