from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAIProvider(ABC):
    @abstractmethod
    def answer_fleet_query(self, query: str, context_data: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def explain_anomaly(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def explain_charging_plan(self, plan_data: Dict[str, Any]) -> str:
        pass