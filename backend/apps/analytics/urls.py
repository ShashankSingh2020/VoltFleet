from django.urls import path
from .views import FleetSummaryAnalyticsView, VehicleEfficiencyAnalyticsView

urlpatterns = [
    path("summary/", FleetSummaryAnalyticsView.as_view(), name="analytics-fleet-summary"),
    path("vehicles/<uuid:vehicle_id>/", VehicleEfficiencyAnalyticsView.as_view(), name="analytics-vehicle-efficiency"),
]