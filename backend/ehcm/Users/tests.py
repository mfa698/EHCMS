from unittest.mock import patch
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase

from contracts.models import AppointmentContract, HonoraryConsul, Mission
from notifications.models import Notification
from . import phone_numbers
from .admin import UserAdminForm
from .models import User
from .services import sms_service
from worklogs.models import WorkLogEntry


class FirstLoginWorkflowTests(APITestCase):

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"
        self.temporary_password = "Temp!TestPassword123"
        self.user = User.objects.create_user(
            email="manager@example.test",
            work_id="MGR-TEST-001",
            full_name="Test Manager",
            phone_number="+10000000000",
            role=User.RoleChoices.MANAGER,
            password=self.temporary_password,
            must_change_password=True,
        )

    def test_role_dashboard_template_route_renders(self):
        response = self.client.get(
            reverse(
                "role-dashboard",
                kwargs={"role": User.RoleChoices.OFFICER},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EHCM Dashboard")

    @patch("Users.authentication_views.send_otp_sms")
    def test_temporary_password_sets_password_before_otp(self, send_otp_sms):
        response = self.client.post(
            reverse("api-login"),
            {
                "work_id": self.user.work_id,
                "password": self.temporary_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["requires_password_change"])
        send_otp_sms.assert_not_called()

        setup_token = response.data["access"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {setup_token}"
        )
        dashboard_response = self.client.get(
            "/api/dashboard/manager/"
        )
        self.assertEqual(dashboard_response.status_code, 403)

        response = self.client.post(
            reverse("api-change-password"),
            {
                "current_password": self.temporary_password,
                "new_password": "Different!Passphrase2026",
                "confirm_password": "Different!Passphrase2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["user"]["must_change_password"])

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {setup_token}"
        )
        stale_setup_response = self.client.post(
            reverse("api-change-password"),
            {
                "current_password": self.temporary_password,
                "new_password": "Another!Passphrase2026",
                "confirm_password": "Another!Passphrase2026",
            },
            format="json",
        )
        self.assertEqual(stale_setup_response.status_code, 403)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        dashboard_response = self.client.get(
            "/api/dashboard/manager/"
        )
        self.assertEqual(dashboard_response.status_code, 200)

    @patch("Users.authentication_views.send_otp_sms")
    def test_existing_user_still_requires_otp(self, send_otp_sms):
        self.user.must_change_password = False
        self.user.save(update_fields=["must_change_password"])

        response = self.client.post(
            reverse("api-login"),
            {
                "work_id": self.user.work_id,
                "password": self.temporary_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["requires_otp"])
        self.assertIn("challenge_id", response.data)
        send_otp_sms.assert_called_once()

    @patch("Users.authentication_views.send_otp_sms", side_effect=RuntimeError("SMS provider rejected credentials"))
    def test_sms_provider_failure_returns_service_unavailable(self, send_otp_sms):
        self.user.must_change_password = False
        self.user.save(update_fields=["must_change_password"])

        response = self.client.post(
            reverse("api-login"),
            {
                "work_id": self.user.work_id,
                "password": self.temporary_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"], "OTP delivery failed. Please try again.")
        self.assertFalse(self.user.login_otps.filter(is_used=False).exists())
        send_otp_sms.assert_called_once()

    def test_admin_form_hashes_new_password_and_preserves_blank_edit(self):
        form = UserAdminForm(
            data={
                "email": "admin-form@example.test",
                "work_id": "MGR-ADMIN-FORM",
                "full_name": "Admin Form Manager",
                "phone_number": "0741082524",
                "role": User.RoleChoices.MANAGER,
                "password": "Replacement!Temp2026",
                "is_active": "on",
                "must_change_password": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.check_password("Replacement!Temp2026"))
        self.assertEqual(user.phone_number, "+254741082524")

        stored_password = user.password
        form = UserAdminForm(
            data={
                "email": user.email,
                "work_id": user.work_id,
                "full_name": user.full_name,
                "phone_number": user.phone_number,
                "role": user.role,
                "password": "",
                "is_active": "on",
                "must_change_password": "on",
            },
            instance=user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.password, stored_password)
        self.assertTrue(user.check_password("Replacement!Temp2026"))


class AfricaTalkingDeliveryReportTests(APITestCase):

    def setUp(self):
        self.url = reverse(
            "africastalking-delivery-report",
            kwargs={"webhook_token": "test-callback-token"},
        )

    @override_settings(AT_DELIVERY_REPORT_TOKEN="test-callback-token")
    def test_accepts_delivery_report_form_post(self):
        response = self.client.post(
            self.url,
            {
                "id": "ATXid_123",
                "status": "Success",
                "phoneNumber": "+254700000000",
                "networkCode": "63902",
                "failureReason": "",
                "retryCount": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"received": True})

    @override_settings(AT_DELIVERY_REPORT_TOKEN="test-callback-token")
    def test_rejects_wrong_callback_token(self):
        response = self.client.post(
            reverse(
                "africastalking-delivery-report",
                kwargs={"webhook_token": "wrong-token"},
            ),
            {"id": "ATXid_123", "status": "Success"},
        )

        self.assertEqual(response.status_code, 404)

    @override_settings(AT_DELIVERY_REPORT_TOKEN="")
    def test_reports_unconfigured_callback_token(self):
        response = self.client.post(
            self.url,
            {"id": "ATXid_123", "status": "Success"},
        )

        self.assertEqual(response.status_code, 503)


class AfricaTalkingInboxCallbackTests(APITestCase):

    def setUp(self):
        self.url = reverse(
            "africastalking-inbox",
            kwargs={"webhook_token": "test-inbox-token"},
        )

    @override_settings(AT_DELIVERY_REPORT_TOKEN="test-inbox-token")
    def test_accepts_inbox_form_post(self):
        response = self.client.post(
            self.url,
            {"from": "+254700000000", "to": "e-HCMS", "text": "Hello", "date": "2026-11-18"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"received": True})

    @override_settings(AT_DELIVERY_REPORT_TOKEN="test-inbox-token")
    def test_rejects_wrong_inbox_token(self):
        response = self.client.post(
            reverse("africastalking-inbox", kwargs={"webhook_token": "wrong"}),
            {"from": "+254700000000", "text": "Hello"},
        )
        self.assertEqual(response.status_code, 404)


class RoleDashboardTests(APITestCase):

    def create_user(self, work_id, role):
        return User.objects.create_user(
            email=f"{work_id.lower()}@example.test",
            work_id=work_id,
            full_name=f"{work_id} User",
            phone_number=f"+1000000{User.objects.count() + 1:04d}",
            role=role,
            password="Strong!TestPassword123",
            must_change_password=False,
        )

    def test_consul_dashboard_returns_frontend_summary_shape(self):
        consul_user = self.create_user("CON-DASH-1", User.RoleChoices.CONSUL)
        mission = Mission.objects.create(name="Test Mission", country="Testland", city="Test City")
        profile = HonoraryConsul.objects.create(
            user=consul_user,
            mission=mission,
            cities_of_operation="Test City Region",
            date_of_first_appointment=timezone.localdate() - timedelta(days=365),
        )
        AppointmentContract.objects.create(
            consul=profile,
            version_number=1,
            reference_number="DASH-CONTRACT-1",
            start_date=timezone.localdate() - timedelta(days=1),
            end_date=timezone.localdate() + timedelta(days=60),
        )
        WorkLogEntry.objects.create(
            consul=profile,
            activity_date=timezone.localdate(),
            title="Test activity",
            description="Dashboard test entry",
        )
        Notification.objects.create(
            recipient=consul_user,
            title="Test notification",
            message="Unread dashboard notification",
        )

        self.client.force_authenticate(user=consul_user)
        response = self.client.get(reverse("consul-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "honorary_consul")
        self.assertEqual(response.data["mission"], "Test City Region")
        self.assertEqual(response.data["contract"]["daysRemaining"], 60)
        self.assertEqual(response.data["unreadNotifications"], 1)
        self.assertEqual(response.data["recentActivity"][0]["title"], "Test activity")

    def test_ambassador_dashboard_only_counts_its_assigned_consuls(self):
        ambassador = self.create_user("AMB-DASH-1", User.RoleChoices.AMBASSADOR)
        assigned_mission = Mission.objects.create(
            name="Assigned Mission", country="Testland", city="Assigned City", head_of_mission=ambassador,
        )
        other_mission = Mission.objects.create(name="Other Mission", country="Testland", city="Other City")
        for index, mission in enumerate((assigned_mission, other_mission), start=1):
            consul_user = self.create_user(f"CONSUL-DASH-{index}", User.RoleChoices.CONSUL)
            profile = HonoraryConsul.objects.create(
                user=consul_user,
                mission=mission,
                cities_of_operation=mission.city,
                date_of_first_appointment=timezone.localdate() - timedelta(days=100),
            )
            AppointmentContract.objects.create(
                consul=profile,
                version_number=1,
                reference_number=f"DASH-AMB-CONTRACT-{index}",
                start_date=timezone.localdate() - timedelta(days=1),
                end_date=timezone.localdate() + timedelta(days=40),
            )

        self.client.force_authenticate(user=ambassador)
        response = self.client.get(reverse("ambassador-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "head_of_mission")
        self.assertEqual(response.data["mission"], "Assigned Mission")
        self.assertEqual(response.data["totals"]["consuls"], 1)
        self.assertEqual(response.data["totals"]["expiring"], 1)
        self.assertEqual(response.data["expiringList"][0]["name"], "CONSUL-DASH-1 User")


class AdminCreateUserEmailTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            email="superadmin@example.test",
            work_id="SUPER-ADMIN-EMAIL",
            full_name="Test Super Admin",
            phone_number="+19999999999",
            role=User.RoleChoices.SUPER_ADMIN,
            password="Strong!AdminPassword123",
            must_change_password=False,
        )
        self.client.force_authenticate(user=self.admin)
        self.payload = {
            "full_name": "New Test User",
            "work_id": "NEW-EMAIL-USER",
            "email": "new-user@example.test",
            "phone_number": "+15550001111",
            "role": User.RoleChoices.CONSUL,
        }

    @patch("Users.admin_views.send_temporary_password_email")
    def test_create_user_sends_temporary_password_via_gmail_service(self, send_email):
        response = self.client.post(reverse("create-user"), self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(work_id="NEW-EMAIL-USER")
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.is_active)
        send_email.assert_called_once()
        self.assertEqual(send_email.call_args.kwargs["recipient"], user.email)
        self.assertEqual(send_email.call_args.kwargs["work_id"], user.work_id)
        self.assertTrue(user.check_password(send_email.call_args.kwargs["temporary_password"]))

    @patch("Users.admin_views.send_temporary_password_email", side_effect=RuntimeError("Gmail unavailable"))
    def test_create_user_disables_account_when_gmail_delivery_fails(self, send_email):
        response = self.client.post(reverse("create-user"), self.payload, format="json")

        self.assertEqual(response.status_code, 503)
        user = User.objects.get(work_id="NEW-EMAIL-USER")
        self.assertFalse(user.is_active)
        send_email.assert_called_once()


class PhoneNumberNormalizationTests(APITestCase):

    def test_normalizes_kenyan_local_and_country_code_formats(self):
        self.assertEqual(
            phone_numbers.normalize_phone_number("0741082524"),
            "+254741082524",
        )
        self.assertEqual(
            phone_numbers.normalize_phone_number("254741082524"),
            "+254741082524",
        )
        self.assertEqual(
            phone_numbers.normalize_phone_number("+254 741-082-524"),
            "+254741082524",
        )

    @patch("Users.services.sms_service.africastalking")
    def test_sms_send_normalizes_kenyan_number_for_provider(self, africastalking):
        africastalking.SMS.send.return_value = {"SMSMessageData": {}}

        result = sms_service.send_otp_sms("0741082524", "123456")

        africastalking.SMS.send.assert_called_once()
        args, _ = africastalking.SMS.send.call_args
        self.assertEqual(args[1], ["+254741082524"])
        self.assertEqual(result, {"SMSMessageData": {}})
