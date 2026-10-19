from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from apps.authentication.permissions import IsFleetOperator
from .models import Fleet, VehicleSpecification, Vehicle
from .serializers import FleetSerializer, VehicleSpecificationSerializer, VehicleSerializer


class TenantScopedQuerysetMixin:
    """
    Restricts querysets strictly to the authenticated user's organization.
    Superusers retain unrestricted visibility.
    """
    def get_user_org(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return None
        membership = user.memberships.filter(is_active=True).first()
        return membership.organization if membership else None

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        org = self.get_user_org()
        if not org:
            return queryset.none()
        return queryset.filter(organization=org)


class FleetViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Fleet.objects.all()
    serializer_class = FleetSerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "depot_location"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        serializer.save(organization=self.get_user_org())


class VehicleSpecificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Global OEM vehicle specs catalog (read-only for operators).
    """
    queryset = VehicleSpecification.objects.all()
    serializer_class = VehicleSpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["make", "model"]
    ordering_fields = ["year", "make", "model"]


class VehicleViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related("specification", "fleet").all()
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated, IsFleetOperator]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["vin", "license_plate", "nickname"]
    ordering_fields = ["license_plate", "current_soc_percent", "odometer_km", "created_at"]

    def perform_create(self, serializer):
        serializer.save(organization=self.get_user_org())