
import calendar
from datetime import timedelta

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contracts.models import AppointmentContract, HonoraryConsul
from notifications.models import Notification
from reports.models import QuarterlyReport
from worklogs.models import WorkLogEntry
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
        today = timezone.localdate()
        profile = HonoraryConsul.objects.select_related("mission").filter(user=request.user).first()
        contract = None
        reports = QuarterlyReport.objects.none()
        work_logs = WorkLogEntry.objects.none()
        mission = ""

        if profile:
            mission = profile.cities_of_operation or profile.mission.name
            contract = AppointmentContract.objects.filter(
                consul=profile,
                is_current=True,
            ).order_by("-start_date").first()
            reports = QuarterlyReport.objects.filter(consul=profile)
            work_logs = WorkLogEntry.objects.filter(consul=profile)

        quarter = (today.month - 1) // 3 + 1
        quarter_end = today.replace(
            month=quarter * 3,
            day=calendar.monthrange(today.year, quarter * 3)[1],
        )
        current_report = reports.filter(year=today.year, quarter=quarter).first()
        report_status = "not_started"
        submitted_at = None
        if current_report:
            report_status = (
                "draft" if current_report.status in {
                    QuarterlyReport.StatusChoices.DRAFT,
                    QuarterlyReport.StatusChoices.REVISION_REQUESTED,
                } else "submitted"
            )
            submitted_at = current_report.submitted_at

        recent_activity = [
            {
                "date": entry.activity_date,
                "title": entry.title,
                "status": "completed" if entry.is_locked else "ongoing",
            }
            for entry in work_logs.order_by("-activity_date", "-created_at")[:5]
        ]
        return Response({
            "user": {"name": request.user.full_name, "role": "honorary_consul"},
            "mission": mission,
            "contract": {
                "appointmentDate": profile.date_of_first_appointment if profile else None,
                "endDate": contract.end_date if contract else None,
                "daysRemaining": contract.days_remaining if contract else None,
            },
            "nextReport": {
                "quarter": f"Q{quarter} {today.year}",
                "dueDate": quarter_end,
            },
            "submission": {
                "quarter": f"Q{quarter} {today.year}",
                "status": report_status,
                "submittedAt": submitted_at,
            },
            "unreadNotifications": Notification.objects.filter(
                recipient=request.user,
                is_read=False,
            ).count(),
            "recentActivity": recent_activity,
        })


class AmbassadorDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        PasswordSetupComplete,
        IsAmbassador
    ]

    def get(self, request):
        today = timezone.localdate()
        activity_cutoff = today - timedelta(days=30)
        profiles = list(
            HonoraryConsul.objects.filter(
                mission__head_of_mission=request.user,
                is_active=True,
            ).select_related("user", "mission")
        )
        profile_ids = [profile.id for profile in profiles]
        contracts = {
            contract.consul_id: contract
            for contract in AppointmentContract.objects.filter(
                consul_id__in=profile_ids,
                is_current=True,
            )
        }
        recent_logs = WorkLogEntry.objects.filter(
            consul_id__in=profile_ids,
            activity_date__gte=activity_cutoff,
        )
        active_consul_ids = set(recent_logs.values_list("consul_id", flat=True).distinct())
        report_queryset = QuarterlyReport.objects.filter(consul_id__in=profile_ids)
        pending_reports = report_queryset.filter(
            status__in=[
                QuarterlyReport.StatusChoices.SUBMITTED,
                QuarterlyReport.StatusChoices.UNDER_REVIEW,
            ]
        ).count()

        attention_list = []
        expiring_list = []
        for profile in profiles:
            contract = contracts.get(profile.id)
            reasons = []
            if contract:
                days_remaining = (contract.end_date - today).days
                if days_remaining <= 90:
                    expiring_list.append({
                        "id": str(profile.id),
                        "name": profile.user.full_name,
                        "endDate": contract.end_date,
                        "daysRemaining": days_remaining,
                    })
                    reasons.append(
                        "Contract expired" if days_remaining < 0
                        else f"Contract ends in {days_remaining} days"
                    )
            if profile.id not in active_consul_ids:
                reasons.append("No activity in the last 30 days")
            if reasons:
                attention_list.append({
                    "id": str(profile.id),
                    "name": profile.user.full_name,
                    "city": profile.mission.city,
                    "reasons": reasons,
                })

        mission = profiles[0].mission.name if profiles else ""
        return Response({
            "user": {"name": request.user.full_name, "role": "head_of_mission"},
            "mission": mission,
            "totals": {
                "consuls": len(profiles),
                "attention": len(attention_list),
                "pendingReports": pending_reports,
                "expiring": len(expiring_list),
            },
            "attentionList": attention_list,
            "expiringList": expiring_list,
            "activity": {
                "active": len(active_consul_ids),
                "total": len(profiles),
                "windowDays": 30,
            },
            "unreadNotifications": Notification.objects.filter(
                recipient=request.user,
                is_read=False,
            ).count(),
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
