import json
import logging
from typing import Dict, Any
from google import genai
from google.genai import types
from .base import BaseAIProvider

logger = logging.getLogger(__name__)


class GeminiAIProvider(BaseAIProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def answer_fleet_query(self, query: str, context_data: Dict[str, Any]) -> str:
        prompt = (
            "You are VoltFleet AI, an expert EV Fleet Intelligence Assistant.\n"
            "Answer the user's question STRICTLY based on the provided JSON data below. "
            "Never invent numbers, vehicles, or metrics. If the evidence is insufficient, state so explicitly.\n\n"
            f"AUTHORIZED FLEET CONTEXT:\n{json.dumps(context_data, default=str)}\n\n"
            f"USER QUESTION: {query}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=800,
                )
            )
            return response.text
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            return f"AI Assistant temporarily unavailable: {str(exc)}"

    def explain_anomaly(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            "Analyze this EV fleet anomaly using the provided evidence.\n"
            "Return a strictly valid JSON object with keys: summary, hypotheses (list of strings), "
            "recommended_actions (list of strings), confidence_score (float 0.0 to 1.0), evidence_grounding (string).\n\n"
            f"ANOMALY EVIDENCE:\n{json.dumps(anomaly_data, default=str)}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )
            return json.loads(response.text)
        except Exception as exc:
            logger.error("Gemini anomaly explanation failed: %s", exc)
            return {
                "summary": f"Automated explanation fallback: {str(exc)}",
                "hypotheses": ["Diagnostic sensor verification required."],
                "recommended_actions": ["Review manual telemetry logs."],
                "confidence_score": 0.50,
                "evidence_grounding": anomaly_data.get("evidence_summary", "")
            }

    def explain_charging_plan(self, plan_data: Dict[str, Any]) -> str:
        prompt = (
            "Explain this deterministic smart charging schedule to a fleet operations manager. "
            "Explain why vehicles were prioritized, how tariff periods were leveraged, and total cost/energy metrics.\n\n"
            f"SCHEDULE DATA:\n{json.dumps(plan_data, default=str)}"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=600,
                )
            )
            return response.text
        except Exception as exc:
            logger.error("Gemini charging plan explanation failed: %s", exc)
            return f"Schedule analysis fallback: {str(exc)}"