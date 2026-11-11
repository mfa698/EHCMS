from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from . import phone_numbers
from .admin import UserAdminForm
from .models import User
from .services import sms_service


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
