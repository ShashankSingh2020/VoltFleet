from django.urls import path
from .views import (
    FleetAIChatView,
    AnomalyExplanationView,
    ChargingPlanExplanationView,
)

urlpatterns = [
    path("chat/", FleetAIChatView.as_view(), name="ai-fleet-chat"),
    path("anomalies/<uuid:anomaly_id>/explain/", AnomalyExplanationView.as_view(), name="ai-anomaly-explain"),
    path("plans/<uuid:plan_id>/explain/", ChargingPlanExplanationView.as_view(), name="ai-plan-explain"),
]