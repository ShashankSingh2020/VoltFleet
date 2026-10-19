import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services import AIAssistantService
from apps.anomalies.models import Anomaly

logger = logging.getLogger(__name__)


def _get_user_org(user):
    org = getattr(user, "organization", None)
    if not org and hasattr(user, "memberships"):
        m = user.memberships.select_related("organization").first()
        if m:
            org = m.organization
    return org


def _resolve_provider_name():
    # Check if AIAssistantService has provider defined on class/module
    provider_cls = getattr(AIAssistantService, "provider", None)
    if provider_cls:
        return provider_cls.__class__.__name__ if hasattr(provider_cls, "__class__") else str(provider_cls)

    # If GEMINI_API_KEY is not configured or in tests, provider defaults to MockAIProvider
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return "MockAIProvider"
    return "GeminiAIProvider"


class FleetAIChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "ai_chat"

    def post(self, request):
        query = request.data.get("query")
        if not query or not str(query).strip():
            return Response({"error": "Query cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        org = _get_user_org(request.user)
        if not org and not request.user.is_superuser:
            return Response({"error": "User does not belong to any organization."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            provider_name = _resolve_provider_name()

            import inspect
            sig = inspect.signature(AIAssistantService.answer_query)
            first_param = list(sig.parameters.keys())[0] if sig.parameters else "user"
            target = org if first_param in ("organization", "org") else request.user

            try:
                answer = AIAssistantService.answer_query(target, str(query).strip())
            except TypeError:
                alt_target = request.user if target is org else org
                answer = AIAssistantService.answer_query(alt_target, str(query).strip())

            return Response({"answer": answer, "provider": provider_name}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception("AI assistant query error: %s", exc)
            return Response(
                {"error": "An internal error occurred while processing your AI request. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AnomalyExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("anomaly_id") or kwargs.get("pk")
        qs = Anomaly.objects.select_related("vehicle")
        if not request.user.is_superuser:
            org = _get_user_org(request.user)
            if not org:
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(organization=org)

        incident = qs.filter(id=pk).first()
        if not incident:
            return Response({"error": "Anomaly incident not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            explanation = AIAssistantService.explain_anomaly(incident)
            return Response(explanation, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception("AI anomaly explanation error: %s", exc)
            return Response(
                {"error": "Unable to generate AI anomaly diagnostics at this time."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChargingPlanExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("plan_id") or kwargs.get("pk")
        from apps.optimizer import models as opt_models
        PlanModel = getattr(opt_models, "ChargingPlan", getattr(opt_models, "ChargingOptimizationPlan", None))

        if PlanModel is None:
            return Response({"error": "Charging plan model not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        qs = PlanModel.objects.all()
        if not request.user.is_superuser:
            org = _get_user_org(request.user)
            if not org:
                return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(organization=org)

        plan = qs.filter(id=pk).first()
        if not plan:
            return Response({"error": "Charging plan not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            explanation = AIAssistantService.explain_plan(plan)
            return Response({"plan_id": str(plan.id), "explanation": explanation}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception("AI plan explanation error: %s", exc)
            return Response(
                {"error": "Unable to generate AI plan explanation at this time."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


AIChatView = FleetAIChatView
ExplainAnomalyView = AnomalyExplanationView
ExplainPlanView = ChargingPlanExplanationView
