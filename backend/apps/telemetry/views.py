import logging
from rest_framework import viewsets, mixins, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TelemetryRecord
from .serializers import TelemetryRecordSerializer, TelemetryIngestBatchSerializer
from .services import TelemetryIngestionService
from apps.authentication.utils import get_active_user_organization

logger = logging.getLogger(__name__)
MAX_BATCH_SIZE = 1000


def _resolve_tenant_org(request, serializer):
    user = request.user
    org = get_active_user_organization(user)
    if not org and user.is_superuser:
        from apps.vehicles.models import Vehicle
        data = serializer.validated_data
        first_item = data[0] if isinstance(data, list) and data else data
        if isinstance(first_item, dict):
            v_id = first_item.get("vehicle_id")
            veh = Vehicle.objects.filter(id=v_id).first()
            if veh:
                org = veh.organization
    return org


class TelemetryBatchIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_data = request.data
        if isinstance(raw_data, dict) and "events" in raw_data:
            raw_data = raw_data["events"]
        elif not isinstance(raw_data, list):
            raw_data = [raw_data]

        if len(raw_data) > MAX_BATCH_SIZE:
            return Response(
                {"error": f"Batch size exceeds maximum limit of {MAX_BATCH_SIZE} events per request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TelemetryIngestBatchSerializer(data=raw_data, many=True)
        serializer.is_valid(raise_exception=True)

        org = _resolve_tenant_org(request, serializer)
        if not org and not request.user.is_superuser:
            return Response(
                {"error": "User does not belong to any active organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created, deduped = TelemetryIngestionService.ingest_batch(
            serializer.validated_data, organization=org
        )
        return Response(
            {
                "status": "success",
                "accepted": created,
                "created": created,
                "ignored_duplicates": deduped,
                "deduplicated": deduped,
            },
            status=status.HTTP_200_OK,
        )


class TelemetrySingleIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TelemetryIngestBatchSerializer(data=[request.data], many=True)
        serializer.is_valid(raise_exception=True)

        org = _resolve_tenant_org(request, serializer)
        if not org and not request.user.is_superuser:
            return Response(
                {"error": "User does not belong to any active organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created, deduped = TelemetryIngestionService.ingest_batch(
            serializer.validated_data, organization=org
        )
        return Response(
            {
                "status": "success",
                "accepted": created,
                "created": created,
                "ignored_duplicates": deduped,
                "deduplicated": deduped,
            },
            status=status.HTTP_200_OK,
        )


class TelemetryHistoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TelemetryRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return TelemetryRecord.objects.none()

        if user.is_superuser:
            return TelemetryRecord.objects.select_related("vehicle").all().order_by("-timestamp")

        org = get_active_user_organization(user)
        if not org:
            return TelemetryRecord.objects.none()

        return TelemetryRecord.objects.filter(
            vehicle__organization=org
        ).select_related("vehicle").order_by("-timestamp")
