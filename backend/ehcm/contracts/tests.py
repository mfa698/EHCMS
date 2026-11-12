from datetime import timedelta
from unittest.mock import patch
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from Users.models import User
from contracts.models import (
    Mission,
    HonoraryConsul,
    AppointmentContract,
    RenewalCase,
)
from contracts.tasks import evaluate_contract_expiries


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def backend_ecosystem(db):
    _ = db
    today = timezone.localdate()

    hq_manager = User.objects.create_user(
        work_id="TEST-HQ-001",
        email="hq.test@mfa.go.ke",
        full_name="Test HQ Director",
        phone_number="+254711000001",
        role=User.RoleChoices.MANAGER,
        password="StrongPass@2026",
        must_change_password=False,
    )

    ambassador_berlin = User.objects.create_user(
        work_id="TEST-AMB-001",
        email="amb.berlin.test@mfa.go.ke",
        full_name="Amb. Berlin Test",
        phone_number="+254711000002",
        role=User.RoleChoices.AMBASSADOR,
        password="StrongPass@2026",
        must_change_password=False,
    )

    ambassador_paris = User.objects.create_user(
        work_id="TEST-AMB-002",
        email="amb.paris.test@mfa.go.ke",
        full_name="Amb. Paris Test",
        phone_number="+254711000003",
        role=User.RoleChoices.AMBASSADOR,
        password="StrongPass@2026",
        must_change_password=False,
    )

    consul_user_1 = User.objects.create_user(
        work_id="TEST-HC-001",
        email="hc1.test@ehcms.org",
        full_name="Consul One",
        phone_number="+254711000004",
        role=User.RoleChoices.CONSUL,
        password="StrongPass@2026",
        must_change_password=False,
    )

    consul_user_2 = User.objects.create_user(
        work_id="TEST-HC-002",
        email="hc2.test@ehcms.org",
        full_name="Consul Two",
        phone_number="+254711000005",
        role=User.RoleChoices.CONSUL,
        password="StrongPass@2026",
        must_change_password=False,
    )

    mission_berlin = Mission.objects.create(
        name="Embassy Berlin Test",
        country="Germany",
        city="Berlin",
        head_of_mission=ambassador_berlin,
    )

    mission_paris = Mission.objects.create(
        name="Embassy Paris Test",
        country="France",
        city="Paris",
        head_of_mission=ambassador_paris,
    )

    hc_1 = HonoraryConsul.objects.create(
        user=consul_user_1,
        mission=mission_berlin,
        cities_of_operation="Hamburg",
        date_of_first_appointment=today - timedelta(days=500),
    )

    hc_2 = HonoraryConsul.objects.create(
        user=consul_user_2,
        mission=mission_paris,
        cities_of_operation="Lyon",
        date_of_first_appointment=today - timedelta(days=400),
    )

    contract_expiring = AppointmentContract.objects.create(
        consul=hc_1,
        version_number=1,
        reference_number="TEST/MFA/001",
        start_date=today - timedelta(days=700),
        end_date=today + timedelta(days=25),
        status=AppointmentContract.StatusChoices.ACTIVE,
        is_current=True,
        authorized_by=hq_manager,
    )

    return {
        "hq_manager": hq_manager,
        "ambassador_berlin": ambassador_berlin,
        "ambassador_paris": ambassador_paris,
        "consul_user_1": consul_user_1,
        "consul_user_2": consul_user_2,
        "mission_berlin": mission_berlin,
        "mission_paris": mission_paris,
        "hc_1": hc_1,
        "hc_2": hc_2,
        "contract_expiring": contract_expiring,
    }


@pytest.mark.django_db
def test_1_users_auth_and_mfa_flow(api_client, backend_ecosystem):
    _ = backend_ecosystem
    with patch("Users.authentication_views.send_otp_sms", return_value=True) as mock_sms:
        login_res = api_client.post(
            "/api/auth/login/",
            {"work_id": "TEST-HQ-001", "password": "StrongPass@2026"},
            format="json",
        )
        assert login_res.status_code == 200
        otp_code = mock_sms.call_args[0][1]
        challenge_id = login_res.data.get("challenge_id")

    verify_res = api_client.post(
        "/api/auth/verify-otp/",
        {"challenge_id": challenge_id, "otp_code": otp_code},
        format="json",
    )
    assert verify_res.status_code == 200
    assert "access" in verify_res.data


@pytest.mark.django_db
def test_2_contracts_rbac_and_consul_api(api_client, backend_ecosystem):
    api_client.force_authenticate(user=backend_ecosystem["consul_user_1"])
    res_consul = api_client.get("/api/contracts/consuls/")
    assert res_consul.status_code == 200
    assert len(res_consul.data) == 1
    assert res_consul.data[0]["work_id"] == "TEST-HC-001"

    api_client.force_authenticate(user=backend_ecosystem["ambassador_paris"])
    res_amb = api_client.get("/api/contracts/consuls/")
    assert res_amb.status_code == 200
    assert len(res_amb.data) == 1
    assert res_amb.data[0]["work_id"] == "TEST-HC-002"

    api_client.force_authenticate(user=backend_ecosystem["hq_manager"])
    res_hq = api_client.get("/api/contracts/consuls/")
    assert res_hq.status_code == 200
    assert len(res_hq.data) == 2


@pytest.mark.django_db
def test_3_worklogs_and_reports_lifecycle(api_client, backend_ecosystem):
    api_client.force_authenticate(user=backend_ecosystem["consul_user_1"])

    log_res = api_client.post(
        "/api/worklogs/",
        {
            "activity_date": str(timezone.localdate()),
            "category": "trade_investment",
            "title": "Bilateral Trade Roundtable",
            "description": "Met with 12 regional importers.",
        },
        format="json",
    )
    assert log_res.status_code == 201
    log_id = log_res.data["id"]

    report_res = api_client.post(
        "/api/reports/",
        {
            "year": 2026,
            "quarter": 4,
            "executive_summary": "Strong Q4 trade engagement.",
            "linked_work_logs": [log_id],
        },
        format="json",
    )
    assert report_res.status_code == 201
    report_id = report_res.data["id"]

    sample_pdf = SimpleUploadedFile("evidence.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
    att_res = api_client.post(
        f"/api/reports/{report_id}/attachments/",
        {"file": sample_pdf},
        format="multipart",
    )
    assert att_res.status_code == 201

    submit_res = api_client.post(f"/api/reports/{report_id}/submit/")
    assert submit_res.status_code == 200
    assert submit_res.data["receipt_number"].startswith("EHCMS-2026Q4-")

    patch_res = api_client.patch(f"/api/worklogs/{log_id}/", {"title": "Tampered"}, format="json")
    assert patch_res.status_code == 400

    api_client.force_authenticate(user=backend_ecosystem["ambassador_berlin"])
    review_res = api_client.post(
        f"/api/reports/{report_id}/review/",
        {"decision": "endorse", "hom_remarks": "Well documented."},
        format="json",
    )
    assert review_res.status_code == 200
    assert review_res.data["status"] == "endorsed"


@pytest.mark.django_db
def test_4_notifications_expiry_and_renewal_audit(api_client, backend_ecosystem, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    contract = backend_ecosystem["contract_expiring"]

    triggered = evaluate_contract_expiries()
    assert triggered == 1
    assert evaluate_contract_expiries() == 0

    api_client.force_authenticate(user=backend_ecosystem["hq_manager"])
    notif_res = api_client.get("/api/notifications/")
    assert notif_res.status_code == 200
    assert len(notif_res.data) >= 1
    notif_id = notif_res.data[0]["id"]

    read_res = api_client.post(f"/api/notifications/{notif_id}/mark-read/")
    assert read_res.status_code == 200

    renewal_case = RenewalCase.objects.get(expiring_contract=contract)
    approve_res = api_client.post(
        f"/api/contracts/renewals/{renewal_case.id}/approve/",
        {
            "reference_number": "TEST/MFA/001-R1",
            "start_date": "2026-12-01",
            "end_date": "2028-12-01",
            "decision_notes": "Renewed for 2 years.",
        },
        format="json",
    )
    assert approve_res.status_code == 200

    contract.refresh_from_db()
    assert contract.is_current is False
    assert contract.status == AppointmentContract.StatusChoices.RENEWED

    audit_res = api_client.get("/api/contracts/audit-logs/")
    assert audit_res.status_code == 200
    actions = [entry["action"] for entry in audit_res.data]
    assert "CONTRACT_RENEWED" in actions
