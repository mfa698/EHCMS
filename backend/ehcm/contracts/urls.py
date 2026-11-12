from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MissionViewSet,
    HonoraryConsulViewSet,
    AppointmentContractViewSet,
    PerformanceEvaluationViewSet,
    RecommendationViewSet,
    RenewalCaseViewSet,
    AuditLogViewSet,
)

router = DefaultRouter()
router.register(r"missions", MissionViewSet, basename="mission")
router.register(r"consuls", HonoraryConsulViewSet, basename="consul")
router.register(r"appointments", AppointmentContractViewSet, basename="appointment")
router.register(r"evaluations", PerformanceEvaluationViewSet, basename="evaluation")
router.register(r"recommendations", RecommendationViewSet, basename="recommendation")
router.register(r"renewals", RenewalCaseViewSet, basename="renewal")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", include(router.urls)),
]
