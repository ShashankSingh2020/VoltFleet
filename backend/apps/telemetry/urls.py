from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TelemetrySingleIngestView,
    TelemetryBatchIngestView,
    TelemetryHistoryViewSet,
)

router = DefaultRouter()
router.register(r"history", TelemetryHistoryViewSet, basename="telemetry-history")

urlpatterns = [
    path("ingest/", TelemetrySingleIngestView.as_view(), name="telemetry-ingest-single"),
    path("ingest/batch/", TelemetryBatchIngestView.as_view(), name="telemetry-ingest-batch"),
    path("", include(router.urls)),
]