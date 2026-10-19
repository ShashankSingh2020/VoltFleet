from rest_framework import views, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.anomalies.models import Anomaly
from apps.optimizer.models import ChargingPlan
from .services import AIAssistantService
from .serializers import ChatQueryRequestSerializer, ChatQueryResponseSerializer


class FleetAIChatView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ChatQueryRequestSerializer, responses={200: ChatQueryResponseSerializer})
    def post(self, request):
        serializer = ChatQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None
        if not org and not request.user.is_superuser:
            return Response({"detail": "User has no active organization."}, status=status.HTTP_403_FORBIDDEN)

        query = serializer.validated_data["query"]
        answer = AIAssistantService.answer_query(organization=org, query=query)
        provider_name = AIAssistantService.get_provider().__class__.__name__

        return Response({
            "query": query,
            "answer": answer,
            "provider": provider_name
        }, status=status.HTTP_200_OK)


class AnomalyExplanationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, anomaly_id):
        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None

        anomaly = Anomaly.objects.filter(id=anomaly_id, organization=org).select_related("vehicle").first()
        if not anomaly and not request.user.is_superuser:
            return Response({"detail": "Anomaly not found."}, status=status.HTTP_404_NOT_FOUND)

        explanation = AIAssistantService.explain_anomaly(anomaly)
        return Response(explanation, status=status.HTTP_200_OK)


class ChargingPlanExplanationView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, plan_id):
        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None

        plan = ChargingPlan.objects.filter(id=plan_id, organization=org).prefetch_related("items__vehicle", "items__charger").first()
        if not plan and not request.user.is_superuser:
            return Response({"detail": "Charging plan not found."}, status=status.HTTP_404_NOT_FOUND)

        explanation = AIAssistantService.explain_plan(plan)
        return Response({"plan_id": str(plan.id), "explanation": explanation}, status=status.HTTP_200_OK)