
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import ChangePasswordSerializer


class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        current_password = serializer.validated_data[
            "current_password"
        ]

        if not request.user.check_password(current_password):
            return Response(
                {"error": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_password = serializer.validated_data["new_password"]

        user = request.user

        user.set_password(new_password)
        user.must_change_password = False

        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "updated_at"
            ]
        )

        # Maintain the current Django session if using session auth.
        update_session_auth_hash(request, user)

        return Response(
            {
                "message": "Password updated successfully.",
                "must_change_password": False,
                "role": user.role
            },
            status=status.HTTP_200_OK
        )
