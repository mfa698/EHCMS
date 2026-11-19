from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from .frontend_compat import (
    ConsulDashboardCompatView,
    ConsulProfileCompatView,
    NotificationsCompatView,
    NotificationReadCompatView,
    NotificationReadAllCompatView,
    WorkLogCompatView,
    WorkLogDetailCompatView,
    ConsulReportsCompatView,
    ConsulReportDraftCompatView,
    ConsulReportSubmitCompatView,
    HomDashboardCompatView,
    HomConsulsCompatView,
    HomReportsCompatView,
    HomReportReviewCompatView,
    HomPerformanceCompatView,
    HomEvaluationsCompatView,
    HomRecommendationsCompatView,
)

urlpatterns = [
    path("", RedirectView.as_view(url="/login/", permanent=False)),
    path("admin/", admin.site.urls),
    path("", include("Users.urls")),
    path("api/contracts/", include("contracts.urls")),
    path("api/worklogs/", include("worklogs.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/notifications/", include("notifications.urls")),

    # Native Frontend Compatibility Endpoints (Honorary Consul & Head of Mission)
    path("consul/dashboard", ConsulDashboardCompatView.as_view()),
    path("consul/profile", ConsulProfileCompatView.as_view()),
    path("consul/notifications", NotificationsCompatView.as_view()),
    path("consul/notifications/<uuid:pk>/read", NotificationReadCompatView.as_view()),
    path("consul/notifications/read-all", NotificationReadAllCompatView.as_view()),
    path("consul/work-log", WorkLogCompatView.as_view()),
    path("consul/work-log/<uuid:pk>", WorkLogDetailCompatView.as_view()),
    path("consul/reports", ConsulReportsCompatView.as_view()),
    path("consul/reports/<uuid:pk>/draft", ConsulReportDraftCompatView.as_view()),
    path("consul/reports/<uuid:pk>/submit", ConsulReportSubmitCompatView.as_view()),

    path("hom/dashboard", HomDashboardCompatView.as_view()),
    path("hom/consuls", HomConsulsCompatView.as_view()),
    path("hom/reports", HomReportsCompatView.as_view()),
    path("hom/reports/<uuid:pk>/review", HomReportReviewCompatView.as_view()),
    path("hom/notifications", NotificationsCompatView.as_view()),
    path("hom/notifications/<uuid:pk>/read", NotificationReadCompatView.as_view()),
    path("hom/notifications/read-all", NotificationReadAllCompatView.as_view()),
    path("hom/performance", HomPerformanceCompatView.as_view()),
    path("hom/evaluations", HomEvaluationsCompatView.as_view()),
    path("hom/recommendations", HomRecommendationsCompatView.as_view()),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
