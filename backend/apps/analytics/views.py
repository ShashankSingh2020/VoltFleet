from rest_framework import views, status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.vehicles.models import Vehicle
from .services import FleetAnalyticsService
from .serializers import FleetSummaryResponseSerializer, VehicleEfficiencyResponseSerializer


class FleetSummaryAnalyticsView(views.APIView):
    """
    Returns aggregated fleet energy, distance, and efficiency analytics for the organization.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="start_time", description="Filter from timestamp (ISO 8601)", required=False, type=str),
            OpenApiParameter(name="end_time", description="Filter up to timestamp (ISO 8601)", required=False, type=str),
            OpenApiParameter(name="fleet_id", description="Filter by Fleet UUID", required=False, type=str),
        ],
        responses={200: FleetSummaryResponseSerializer}
    )
    def get(self, request):
        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None
        if not org and not request.user.is_superuser:
            return Response({"detail": "User has no active organization."}, status=status.HTTP_403_FORBIDDEN)

        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")
        fleet_id = request.query_params.get("fleet_id")

        summary = FleetAnalyticsService.get_fleet_summary(
            organization=org,
            start_time=start_time,
            end_time=end_time,
            fleet_id=fleet_id
        )
        return Response(FleetSummaryResponseSerializer(summary).data, status=status.HTTP_200_OK)


class VehicleEfficiencyAnalyticsView(views.APIView):
    """
    Returns interval performance and consumption analytics for a single vehicle.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="start_time", description="Filter from timestamp (ISO 8601)", required=False, type=str),
            OpenApiParameter(name="end_time", description="Filter up to timestamp (ISO 8601)", required=False, type=str),
        ],
        responses={200: VehicleEfficiencyResponseSerializer}
    )
    def get(self, request, vehicle_id):
        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None

        vehicle = Vehicle.objects.filter(id=vehicle_id, organization=org).first()
        if not vehicle and not request.user.is_superuser:
            return Response({"detail": "Vehicle not found in your organization."}, status=status.HTTP_404_NOT_FOUND)
        elif not vehicle:
            vehicle = Vehicle.objects.filter(id=vehicle_id).first()
            if not vehicle:
                return Response({"detail": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND)

        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")

        stats = FleetAnalyticsService.get_vehicle_efficiency(
            vehicle=vehicle,
            start_time=start_time,
            end_time=end_time
        )
        return Response(VehicleEfficiencyResponseSerializer(stats).data, status=status.HTTP_200_OK)