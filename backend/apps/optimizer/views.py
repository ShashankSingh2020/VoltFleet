from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema
from apps.authentication.permissions import IsFleetOperator
from apps.vehicles.views import TenantScopedQuerysetMixin
from .models import ChargingPlan, ChargingPlanItem
from .serializers import (
    ChargingPlanSerializer,
    OptimizeRequestSerializer,
)
from .engine import SmartChargingOptimizer


class ChargingPlanViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ChargingPlan.objects.prefetch_related("items").all()
    serializer_class = ChargingPlanSerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]

    @extend_schema(request=OptimizeRequestSerializer, responses={201: ChargingPlanSerializer})
    @action(detail=False, methods=["post"], url_path="generate")
    def generate_plan(self, request):
        """
        Triggers the deterministic smart charging optimization engine for the tenant's fleet.
        """
        serializer = OptimizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None
        if not org and not request.user.is_superuser:
            return Response({"detail": "User has no active organization."}, status=status.HTTP_403_FORBIDDEN)

        validated = serializer.validated_data
        result = SmartChargingOptimizer.run(
            organization=org,
            horizon_start=validated["horizon_start"],
            horizon_end=validated["horizon_end"],
            vehicle_ids=validated.get("vehicle_ids"),
            charger_ids=validated.get("charger_ids")
        )

        with transaction.atomic():
            plan = ChargingPlan.objects.create(
                organization=org,
                title=validated.get("title", "Optimization Run"),
                horizon_start=validated["horizon_start"],
                horizon_end=validated["horizon_end"],
                status=ChargingPlan.PlanStatus.ACTIVE if result["items"] else ChargingPlan.PlanStatus.FAILED,
                total_vehicles_scheduled=len(result["items"]),
                total_energy_kwh=result["total_energy_kwh"],
                total_estimated_cost=result["total_estimated_cost"],
                algorithm_metadata={
                    **result["metadata"],
                    "unmet_vehicles": result["unmet_vehicles"]
                }
            )

            plan_items = [
                ChargingPlanItem(
                    plan=plan,
                    vehicle=item["vehicle"],
                    charger=item["charger"],
                    scheduled_start=item["start"],
                    scheduled_end=item["end"],
                    energy_to_deliver_kwh=item["energy"],
                    estimated_cost=item["cost"],
                    target_soc_percent=item["target_soc"],
                    is_feasible=item["is_feasible"],
                    notes=item["notes"],
                )
                for item in result["items"]
            ]
            ChargingPlanItem.objects.bulk_create(plan_items)

        return Response(ChargingPlanSerializer(plan).data, status=status.HTTP_201_CREATED)