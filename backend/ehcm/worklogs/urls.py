from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkLogEntryViewSet

router = DefaultRouter()
router.register(r"", WorkLogEntryViewSet, basename="worklog")

urlpatterns = [
    path("", include(router.urls)),
]
