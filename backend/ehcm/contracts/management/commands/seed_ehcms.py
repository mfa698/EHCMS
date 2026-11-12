from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from Users.models import User
from contracts.models import (
    Mission,
    HonoraryConsul,
    AppointmentContract,
    PerformanceEvaluation,
    Recommendation,
    RenewalCase,
    AuditLog,
)
from worklogs.models import WorkLogEntry
from reports.models import QuarterlyReport
from notifications.models import Notification


class Command(BaseCommand):
    help = "Initializes sample data across Users, Missions, Consuls, Contracts, WorkLogs, Reports, and Notifications."

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()

        # 1. Create Role Users (must_change_password=False for immediate API testing)
        hq_manager, _ = User.objects.get_or_create(
            email="director.dgpda@mfa.go.ke",
            defaults={
                "work_id": "MFDA-HQ-001",
                "full_name": "Director General Diaspora Affairs",
                "phone_number": "+254700000101",
                "role": User.RoleChoices.MANAGER,
                "is_staff": True,
                "must_change_password": False,
            },
        )
        hq_manager.set_password("StrongPass@2026")
        hq_manager.save()

        ambassador, _ = User.objects.get_or_create(
            email="amb.berlin@mfa.go.ke",
            defaults={
                "work_id": "MFDA-AMB-010",
                "full_name": "Amb. Grace Wanjiku",
                "phone_number": "+254700000102",
                "role": User.RoleChoices.AMBASSADOR,
                "must_change_password": False,
            },
        )
        ambassador.set_password("StrongPass@2026")
        ambassador.save()

        consul_user_1, _ = User.objects.get_or_create(
            email="hc.hamburg@ehcms.org",
            defaults={
                "work_id": "HC-GER-001",
                "full_name": "Dr. Lukas Weber",
                "phone_number": "+254700000103",
                "role": User.RoleChoices.CONSUL,
                "must_change_password": False,
            },
        )
        consul_user_1.set_password("StrongPass@2026")
        consul_user_1.save()

        consul_user_2, _ = User.objects.get_or_create(
            email="hc.munich@ehcms.org",
            defaults={
                "work_id": "HC-GER-002",
                "full_name": "Sabine Keller",
                "phone_number": "+254700000104",
                "role": User.RoleChoices.CONSUL,
                "must_change_password": False,
            },
        )
        consul_user_2.set_password("StrongPass@2026")
        consul_user_2.save()

        # 2. Create Mission
        mission, _ = Mission.objects.get_or_create(
            name="Embassy of the Republic of Kenya, Berlin",
            defaults={
                "country": "Germany",
                "city": "Berlin",
                "head_of_mission": ambassador,
                "latitude": 52.520008,
                "longitude": 13.404954,
            },
        )

        # 3. Create Honorary Consul Profiles
        hc_1, _ = HonoraryConsul.objects.get_or_create(
            user=consul_user_1,
            defaults={
                "mission": mission,
                "cities_of_operation": "Hamburg, Bremen",
                "office_address": "HafenCity Plaza 14, 20457 Hamburg",
                "nationality": "German",
                "date_of_first_appointment": today - timedelta(days=700),
            },
        )

        hc_2, _ = HonoraryConsul.objects.get_or_create(
            user=consul_user_2,
            defaults={
                "mission": mission,
                "cities_of_operation": "Munich, Bavaria",
                "office_address": "Maximilianstrasse 22, 80539 Munich",
                "nationality": "German",
                "date_of_first_appointment": today - timedelta(days=365),
            },
        )

        # 4. Create Contracts (one expiring in 28 days to trigger 30-day alert; one active)
        contract_1, _ = AppointmentContract.objects.get_or_create(
            reference_number="MFA/HC/GER/2024/01",
            defaults={
                "consul": hc_1,
                "version_number": 1,
                "start_date": today - timedelta(days=702),
                "end_date": today + timedelta(days=28),
                "status": AppointmentContract.StatusChoices.EXPIRING_SOON,
                "is_current": True,
                "authorized_by": hq_manager,
            },
        )

        AppointmentContract.objects.get_or_create(
            reference_number="MFA/HC/GER/2025/02",
            defaults={
                "consul": hc_2,
                "version_number": 1,
                "start_date": today - timedelta(days=365),
                "end_date": today + timedelta(days=365),
                "status": AppointmentContract.StatusChoices.ACTIVE,
                "is_current": True,
                "authorized_by": hq_manager,
            },
        )

        # 5. Create WorkLog Entries
        log_1, _ = WorkLogEntry.objects.get_or_create(
            consul=hc_1,
            title="Kenya-Hamburg Maritime Trade Forum",
            defaults={
                "activity_date": today - timedelta(days=20),
                "category": WorkLogEntry.ActivityCategory.TRADE_INVESTMENT,
                "description": "Hosted 18 German logistics investors exploring Mombasa port partnerships.",
                "location": "Hamburg Chamber of Commerce",
                "outcomes": "3 MoU follow-up delegations scheduled.",
            },
        )

        WorkLogEntry.objects.get_or_create(
            consul=hc_1,
            title="Diaspora Consular Document Clinic",
            defaults={
                "activity_date": today - timedelta(days=5),
                "category": WorkLogEntry.ActivityCategory.DIASPORA_WELFARE,
                "description": "Assisted 42 Kenyan citizens with emergency travel certificates and passport guidance.",
                "location": "Honorary Consulate Hamburg",
            },
        )

        # 6. Create Quarterly Report (Draft linked to log_1)
        report_1, _ = QuarterlyReport.objects.get_or_create(
            consul=hc_1,
            year=today.year,
            quarter=3,
            version=1,
            defaults={
                "executive_summary": "Strong trade engagement and diaspora support across Northern Germany.",
                "trade_and_investment": "Facilitated maritime logistics roundtable in Hamburg.",
                "diaspora_and_consular_services": "Processed 42 consular assistance cases.",
                "status": QuarterlyReport.StatusChoices.DRAFT,
            },
        )
        report_1.linked_work_logs.add(log_1)

        # 7. Create Performance Evaluation, Recommendation & Open Renewal Case
        PerformanceEvaluation.objects.get_or_create(
            consul=hc_1,
            period_label=f"{today.year}-Q3",
            defaults={
                "evaluated_by": ambassador,
                "rating_score": 5,
                "summary": "Exemplary trade promotion and responsive consular support.",
            },
        )

        rec_1, _ = Recommendation.objects.get_or_create(
            consul=hc_1,
            contract=contract_1,
            defaults={
                "submitted_by": ambassador,
                "decision": Recommendation.DecisionChoices.RENEW,
                "justification": "Consistently exceeds trade and diaspora KPIs.",
            },
        )

        RenewalCase.objects.get_or_create(
            consul=hc_1,
            expiring_contract=contract_1,
            defaults={
                "hom_recommendation": rec_1,
                "status": RenewalCase.StatusChoices.UNDER_REVIEW,
            },
        )

        # 8. Seed Initial Notification & AuditLog
        Notification.objects.get_or_create(
            recipient=hq_manager,
            title="Contract Expiring in 28 Days: Dr. Lukas Weber",
            defaults={
                "category": Notification.CategoryChoices.EXPIRY_30,
                "message": "Contract MFA/HC/GER/2024/01 expires in 28 days. Renewal case is ready for HQ decision.",
                "related_entity_type": "AppointmentContract",
                "related_entity_id": str(contract_1.id),
            },
        )

        AuditLog.objects.get_or_create(
            action="SYSTEM_SEED_INITIALIZED",
            entity_type="System",
            entity_id="initial-seed",
            defaults={"actor": hq_manager, "after_state": {"seeded": True}},
        )

        self.stdout.write(self.style.SUCCESS("e-HCMS database initialized with sample data across all apps!"))
