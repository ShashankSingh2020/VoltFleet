from typing import Dict, Any
from .base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    def answer_fleet_query(self, query: str, context_data: Dict[str, Any]) -> str:
        summary = context_data.get("summary", {})
        total_v = summary.get("total_vehicles", 0)
        dist = summary.get("total_distance_km", "0.0")
        energy = summary.get("total_energy_kwh", "0.0")
        return (
            f"[Grounded Analysis] Your fleet currently operates {total_v} active vehicles. "
            f"Over the queried window, total recorded distance is {dist} km with net energy "
            f"consumption of {energy} kWh. No ungrounded speculation detected."
        )

    def explain_anomaly(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        anomaly_type = anomaly_data.get("anomaly_type", "UNKNOWN")
        observed = anomaly_data.get("observed_value", "N/A")
        return {
            "summary": f"Detected {anomaly_type} with observed reading of {observed}.",
            "hypotheses": [
                "Ambient temperature elevation combined with fast DC charging rate.",
                "Potential coolant loop pump restriction or degradation."
            ],
            "recommended_actions": [
                "Inspect liquid coolant reservoir and pump pressure.",
                "Limit charging power to AC Level 2 until thermal diagnostic clears."
            ],
            "confidence_score": 0.92,
            "evidence_grounding": anomaly_data.get("evidence_summary", "")
        }

    def explain_charging_plan(self, plan_data: Dict[str, Any]) -> str:
        total_v = plan_data.get("total_vehicles_scheduled", 0)
        total_energy = plan_data.get("total_energy_kwh", "0.0")
        raw_cost = plan_data.get("total_estimated_cost")
        cost_str = f"" if raw_cost else ".00"
        return (
            f"The optimization plan successfully scheduled {total_v} vehicles to receive {total_energy} kWh "
            f"of energy at an estimated electricity cost of {cost_str}. Vehicles with earlier departure deadlines "
            f"were allocated priority slots, and charging was biased towards off-peak tariff periods."
        )