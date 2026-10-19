from decimal import Decimal
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import User, Organization, Membership
from apps.vehicles.models import Fleet, VehicleSpecification, Vehicle


@pytest.mark.django_db
class TestVehicleFleetAPI:
    def setup_method(self):
        self.client = APIClient()

        # Organization 1 & Operator
        self.org1 = Organization.objects.create(name="Alpha Logistics", slug="alpha-logistics")
        self.user1 = User.objects.create_user(email="alpha@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user1, organization=self.org1, role=Membership.RoleChoices.FLEET_OPERATOR)

        # Organization 2 & Operator
        self.org2 = Organization.objects.create(name="Beta Delivery", slug="beta-delivery")
        self.user2 = User.objects.create_user(email="beta@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user2, organization=self.org2, role=Membership.RoleChoices.FLEET_OPERATOR)

        # Vehicle Specification (e.g. 75 kWh battery, 18 kWh/100km)
        self.spec = VehicleSpecification.objects.create(
            make="VoltMotors",
            model="TransitCargo",
            year=2025,
            usable_battery_capacity_kwh=Decimal("75.0"),
            max_ac_charging_power_kw=Decimal("11.0"),
            max_dc_charging_power_kw=Decimal("150.0"),
            efficiency_kwh_per_100km=Decimal("20.0"),
        )

        # Fleet and Vehicle belonging to Org 1
        self.fleet1 = Fleet.objects.create(organization=self.org1, name="North Hub Fleet")
        self.vehicle1 = Vehicle.objects.create(
            organization=self.org1,
            fleet=self.fleet1,
            specification=self.spec,
            vin="1V9DEADBEEF123456",
            license_plate="EV-ALPHA-01",
            current_soc_percent=Decimal("80.0"),
            odometer_km=Decimal("1500.0"),
        )

    def test_estimated_range_calculation(self):
        # 75 kWh * 80% = 60 kWh battery remaining.
        # At 20.0 kWh/100km: (60 / 20) * 100 = 300.0 km range.
        assert self.vehicle1.estimated_range_km == Decimal("300.0")

    def test_cross_tenant_isolation(self):
        # Authenticate as Org 2 user
        self.client.force_authenticate(user=self.user2)
        url = reverse("vehicle-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Org 2 user must NOT see Org 1's vehicles
        assert response.data["count"] == 0

        # Authenticate as Org 1 user
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["license_plate"] == "EV-ALPHA-01"

    def test_odometer_cannot_decrease(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse("vehicle-detail", kwargs={"pk": self.vehicle1.id})
        # Attempt to reduce odometer from 1500 to 1200 km
        patch_payload = {"odometer_km": "1200.00"}
        response = self.client.patch(url, patch_payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "odometer_km" in response.data