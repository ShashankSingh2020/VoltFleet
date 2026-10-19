from django.conf import settings
from .providers.base import BaseAIProvider
from .providers.mock_provider import MockAIProvider
from .providers.gemini_provider import GeminiAIProvider
from .tools import FleetTools
from .schemas import AnomalyExplanationSchema


class AIAssistantService:
    @classmethod
    def get_provider(cls) -> BaseAIProvider:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if api_key and api_key.strip() and api_key != "your_gemini_api_key_here":
            model_name = getattr(settings, "GEMINI_MODEL_NAME", "gemini-2.5-flash")
            return GeminiAIProvider(api_key=api_key, model_name=model_name)
        return MockAIProvider()

    @classmethod
    def answer_query(cls, organization, query: str) -> str:
        provider = cls.get_provider()
        context = {
            "summary": FleetTools.get_fleet_summary(organization),
            "anomalies": FleetTools.get_unresolved_anomalies(organization),
            "latest_charging_plan": FleetTools.get_latest_charging_plan(organization),
        }
        return provider.answer_fleet_query(query=query, context_data=context)

    @classmethod
    def explain_anomaly(cls, anomaly) -> dict:
        provider = cls.get_provider()
        payload = {
            "anomaly_id": str(anomaly.id),
            "vehicle_plate": anomaly.vehicle.license_plate,
            "anomaly_type": anomaly.anomaly_type,
            "severity": anomaly.severity,
            "observed_value": anomaly.observed_value,
            "threshold_value": anomaly.threshold_value,
            "evidence_summary": anomaly.evidence_summary,
            "context_data": anomaly.context_data,
        }
        raw_explanation = provider.explain_anomaly(payload)
        validated = AnomalyExplanationSchema(**raw_explanation)
        return validated.model_dump()

    @classmethod
    def explain_plan(cls, plan) -> str:
        provider = cls.get_provider()
        payload = {
            "plan_id": str(plan.id),
            "title": plan.title,
            "status": plan.status,
            "total_vehicles_scheduled": plan.total_vehicles_scheduled,
            "total_energy_kwh": str(plan.total_energy_kwh),
            "total_estimated_cost": str(plan.total_estimated_cost),
            "items": [
                {
                    "vehicle": item.vehicle.license_plate,
                    "charger": item.charger.identifier,
                    "start": item.scheduled_start.isoformat(),
                    "end": item.scheduled_end.isoformat(),
                    "energy_kwh": str(item.energy_to_deliver_kwh),
                    "cost": str(item.estimated_cost),
                }
                for item in plan.items.all()
            ]
        }
        return provider.explain_charging_plan(payload)