from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.authentication.permissions import IsFleetOperator
from apps.vehicles.views import TenantScopedQuerysetMixin
from .models import Anomaly, AnomalyResolutionLog
from .serializers import AnomalySerializer, AnomalyActionSerializer
from .detector import AnomalyDetectionEngine


class AnomalyViewSet(TenantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Anomaly.objects.prefetch_related("resolution_logs").all()
    serializer_class = AnomalySerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["vehicle__license_plate", "anomaly_type", "evidence_summary"]
    ordering_fields = ["detected_at", "severity", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        severity_filter = self.request.query_params.get("severity")
        vehicle_id = self.request.query_params.get("vehicle_id")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if severity_filter:
            qs = qs.filter(severity=severity_filter)
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        return qs

    @extend_schema(responses={200: dict})
    @action(detail=False, methods=["post"], url_path="scan")
    def run_scan(self, request):
        """
        Runs an on-demand anomaly scan across the organization's fleet.
        """
        org = self.get_user_org()
        if not org and not request.user.is_superuser:
            return Response({"detail": "No active organization."}, status=status.HTTP_403_FORBIDDEN)

        detected = AnomalyDetectionEngine.scan_organization(org)
        return Response({
            "status": "scan_complete",
            "new_anomalies_detected": len(detected),
            "anomalies": AnomalySerializer(detected, many=True).data
        }, status=status.HTTP_200_OK)

    @extend_schema(request=AnomalyActionSerializer, responses={200: AnomalySerializer})
    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        anomaly = self.get_object()
        serializer = AnomalyActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        anomaly.status = Anomaly.Status.ACKNOWLEDGED
        anomaly.save(update_fields=["status", "updated_at"])

        AnomalyResolutionLog.objects.create(
            anomaly=anomaly,
            action_by=request.user,
            action="ACKNOWLEDGE",
            notes=serializer.validated_data.get("notes", "")
        )
        anomaly.refresh_from_db()
        return Response(AnomalySerializer(anomaly).data, status=status.HTTP_200_OK)

    @extend_schema(request=AnomalyActionSerializer, responses={200: AnomalySerializer})
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        anomaly = self.get_object()
        serializer = AnomalyActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        anomaly.status = Anomaly.Status.RESOLVED
        anomaly.save(update_fields=["status", "updated_at"])

        AnomalyResolutionLog.objects.create(
            anomaly=anomaly,
            action_by=request.user,
            action="RESOLVE",
            notes=serializer.validated_data.get("notes", "")
        )
        anomaly.refresh_from_db()
        return Response(AnomalySerializer(anomaly).data, status=status.HTTP_200_OK)