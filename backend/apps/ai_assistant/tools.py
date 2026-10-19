from typing import Dict, Any
from apps.anomalies.models import Anomaly
from apps.optimizer.models import ChargingPlan
from apps.analytics.services import FleetAnalyticsService


class FleetTools:
    @staticmethod
    def get_fleet_summary(organization) -> Dict[str, Any]:
        return FleetAnalyticsService.get_fleet_summary(organization=organization)

    @staticmethod
    def get_unresolved_anomalies(organization) -> Dict[str, Any]:
        anomalies = Anomaly.objects.filter(
            organization=organization,
            status__in=[Anomaly.Status.OPEN, Anomaly.Status.ACKNOWLEDGED]
        ).values("id", "vehicle__license_plate", "anomaly_type", "severity", "observed_value", "detected_at")
        return {"unresolved_count": len(anomalies), "anomalies": list(anomalies)}

    @staticmethod
    def get_latest_charging_plan(organization) -> Dict[str, Any]:
        plan = ChargingPlan.objects.filter(organization=organization).order_by("-created_at").first()
        if not plan:
            return {"detail": "No charging plans found."}
        return {
            "plan_id": str(plan.id),
            "status": plan.status,
            "vehicles_scheduled": plan.total_vehicles_scheduled,
            "total_energy_kwh": str(plan.total_energy_kwh),
            "total_estimated_cost": str(plan.total_estimated_cost),
        }