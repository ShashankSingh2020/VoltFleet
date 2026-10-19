from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from apps.authentication.permissions import IsFleetOperator
from apps.vehicles.views import TenantScopedQuerysetMixin
from .models import ChargingStation, Charger, TariffPeriod, ChargingSession
from .serializers import (
    ChargingStationSerializer,
    ChargerSerializer,
    TariffPeriodSerializer,
    ChargingSessionSerializer,
)


class ChargingStationViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ChargingStation.objects.prefetch_related("chargers").all()
    serializer_class = ChargingStationSerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "location_address"]
    ordering_fields = ["name", "total_grid_capacity_kw", "created_at"]

    def perform_create(self, serializer):
        serializer.save(organization=self.get_user_org())


class ChargerViewSet(viewsets.ModelViewSet):
    """
    Chargers inherit organization scope from their parent ChargingStation.
    """
    serializer_class = ChargerSerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["identifier", "station__name"]
    ordering_fields = ["identifier", "max_output_power_kw", "status"]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Charger.objects.none()
        if user.is_superuser:
            return Charger.objects.all()
        membership = user.memberships.filter(is_active=True).first()
        if not membership:
            return Charger.objects.none()
        return Charger.objects.filter(station__organization=membership.organization)


class TariffPeriodViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TariffPeriod.objects.all()
    serializer_class = TariffPeriodSerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["start_time", "cost_per_kwh"]

    def perform_create(self, serializer):
        serializer.save(organization=self.get_user_org())


class ChargingSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChargingSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["start_time", "end_time", "energy_delivered_kwh"]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return ChargingSession.objects.none()
        if user.is_superuser:
            return ChargingSession.objects.all()
        membership = user.memberships.filter(is_active=True).first()
        if not membership:
            return ChargingSession.objects.none()
        return ChargingSession.objects.filter(charger__station__organization=membership.organization)