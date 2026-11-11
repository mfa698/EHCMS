
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import ChangePasswordSerializer
from .permissions import CanSetPassword


class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated, CanSetPassword]

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

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Password updated successfully.",
                "must_change_password": False,
                "role": user.role,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "work_id": user.work_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "must_change_password": False,
                }
            },
            status=status.HTTP_200_OK
        )
