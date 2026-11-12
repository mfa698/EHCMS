from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuarterlyReportViewSet

router = DefaultRouter()
router.register(r"", QuarterlyReportViewSet, basename="quarterly-report")

urlpatterns = [
    path("", include(router.urls)),
]
