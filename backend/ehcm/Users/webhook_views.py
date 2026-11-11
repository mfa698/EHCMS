import logging
import secrets

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


logger = logging.getLogger(__name__)


def _safe_log_value(value):
    return str(value or "").replace("\r", " ").replace("\n", " ")[:160]


class AfricaTalkingDeliveryReportView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request, webhook_token):
        configured_token = settings.AT_DELIVERY_REPORT_TOKEN
        if not configured_token:
            return Response(
                {"error": "Delivery report callback is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not secrets.compare_digest(webhook_token, configured_token):
            return Response(
                {"error": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        message_id = request.data.get("id")
        delivery_status = request.data.get("status")
        if not message_id or not delivery_status:
            return Response(
                {"error": "Message id and delivery status are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Africa's Talking SMS delivery report: id=%s status=%s failure_reason=%s",
            _safe_log_value(message_id),
            _safe_log_value(delivery_status),
            _safe_log_value(request.data.get("failureReason")),
        )

        return Response(
            {"received": True},
            status=status.HTTP_200_OK,
        )
