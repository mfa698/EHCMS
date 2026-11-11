
from django.urls import path
from django.views.generic import TemplateView

from .authentication_views import (
    LoginView,
    VerifyLoginOTPView
)

from .admin_views import (
    CreateUserView,
    UserListView,
    DeactivateUserView
)

from .password_views import ChangePasswordView

from .dashboard_views import (
    SuperAdminDashboardView,
    ConsulDashboardView,
    AmbassadorDashboardView,
    ManagerDashboardView,
    OfficerDashboardView
)
from .webhook_views import AfricaTalkingDeliveryReportView

urlpatterns = [

    # FRONTEND TEMPLATE PAGES

    path(
        "login/",
        TemplateView.as_view(template_name="Users/login.html"),
        name="login-page"
    ),

    path(
        "verify-otp/",
        TemplateView.as_view(template_name="Users/verify_otp.html"),
        name="verify-otp-page"
    ),

    path(
        "change-password/",
        TemplateView.as_view(template_name="Users/change_password.html"),
        name="change-password-page"
    ),

    path(
        "dashboard/<slug:role>/",
        TemplateView.as_view(template_name="Users/dashboard.html"),
        name="role-dashboard"
    ),

    # CENTRAL AUTHENTICATION

    path(
        "api/auth/login/",
        LoginView.as_view(),
        name="api-login"
    ),

    path(
        "api/auth/verify-otp/",
        VerifyLoginOTPView.as_view(),
        name="api-verify-otp"
    ),

    path(
        "api/webhooks/africastalking/delivery/<str:webhook_token>/",
        AfricaTalkingDeliveryReportView.as_view(),
        name="africastalking-delivery-report"
    ),

    # PASSWORD MANAGEMENT

    path(
        "api/auth/change-password/",
        ChangePasswordView.as_view(),
        name="api-change-password"
    ),

    # SUPER ADMIN USER MANAGEMENT

    path(
        "api/admin/users/create/",
        CreateUserView.as_view(),
        name="create-user"
    ),

    path(
        "api/admin/users/",
        UserListView.as_view(),
        name="user-list"
    ),

    path(
        "api/admin/users/<uuid:user_id>/deactivate/",
        DeactivateUserView.as_view(),
        name="deactivate-user"
    ),

    # ROLE DASHBOARDS

    path(
        "api/dashboard/super-admin/",
        SuperAdminDashboardView.as_view()
    ),

    path(
        "api/dashboard/consul/",
        ConsulDashboardView.as_view()
    ),

    path(
        "api/dashboard/ambassador/",
        AmbassadorDashboardView.as_view()
    ),

    path(
        "api/dashboard/manager/",
        ManagerDashboardView.as_view()
    ),

    path(
        "api/dashboard/officer/",
        OfficerDashboardView.as_view()
    ),

]
