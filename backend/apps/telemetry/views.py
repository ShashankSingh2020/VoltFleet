from rest_framework import status, views, permissions, viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.authentication.permissions import IsFleetOperator
from apps.vehicles.views import TenantScopedQuerysetMixin
from .models import TelemetryRecord
from .serializers import (
    TelemetryIngestInputSerializer,
    TelemetryBatchIngestSerializer,
    TelemetryEventSerializer,
)
from .services import TelemetryIngestionService


class TelemetrySingleIngestView(views.APIView):
    """
    Ingests a single EV telemetry packet.
    """
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]

    @extend_schema(request=TelemetryIngestInputSerializer, responses={201: dict})
    def post(self, request):
        serializer = TelemetryIngestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None
        if not org and not request.user.is_superuser:
            return Response({"detail": "User has no active organization."}, status=status.HTTP_403_FORBIDDEN)

        accepted, ignored = TelemetryIngestionService.ingest_batch(
            [serializer.validated_data], organization=org
        )
        return Response(
            {"status": "processed", "accepted": accepted, "ignored_duplicates": ignored},
            status=status.HTTP_201_CREATED if accepted > 0 else status.HTTP_200_OK
        )


class TelemetryBatchIngestView(views.APIView):
    """
    Ingests a bulk array of up to 500 telemetry events with automatic deduplication.
    """
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]

    @extend_schema(request=TelemetryBatchIngestSerializer, responses={200: dict})
    def post(self, request):
        serializer = TelemetryBatchIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = request.user.memberships.filter(is_active=True).first()
        org = membership.organization if membership else None
        if not org and not request.user.is_superuser:
            return Response({"detail": "User has no active organization."}, status=status.HTTP_403_FORBIDDEN)

        events = serializer.validated_data["events"]
        accepted, ignored = TelemetryIngestionService.ingest_batch(events, organization=org)

        return Response(
            {
                "status": "success",
                "total_received": len(events),
                "accepted": accepted,
                "ignored_duplicates": ignored,
            },
            status=status.HTTP_200_OK
        )


class TelemetryHistoryViewSet(TenantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for inspecting time-indexed telemetry logs per vehicle.
    """
    queryset = TelemetryRecord.objects.select_related("vehicle").all()
    serializer_class = TelemetryEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        vehicle_id = self.request.query_params.get("vehicle_id")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        start_time = self.request.query_params.get("start_time")
        end_time = self.request.query_params.get("end_time")
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)
        return queryset