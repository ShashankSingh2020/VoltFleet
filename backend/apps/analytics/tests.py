from decimal import Decimal
from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import User, Organization, Membership
from apps.vehicles.models import Vehicle, VehicleSpecification
from apps.telemetry.models import TelemetryRecord


@pytest.mark.django_db
class TestAnalyticsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="Apex Fleet Services", slug="apex-fleet-services")
        self.user = User.objects.create_user(email="analyst@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user, organization=self.org, role=Membership.RoleChoices.ANALYST)

        self.spec = VehicleSpecification.objects.create(
            make="VoltExpress",
            model="CargoMax",
            year=2025,
            usable_battery_capacity_kwh=Decimal("100.0"),
            max_ac_charging_power_kw=Decimal("22.0"),
            max_dc_charging_power_kw=Decimal("150.0"),
            efficiency_kwh_per_100km=Decimal("20.0"),
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9ANALYTICS12345",
            license_plate="EV-ANALYTICS-01",
            current_soc_percent=Decimal("70.0"),
            odometer_km=Decimal("1000.0"),
        )
        self.summary_url = reverse("analytics-fleet-summary")
        self.vehicle_url = reverse("analytics-vehicle-efficiency", kwargs={"vehicle_id": self.vehicle.id})

    def test_efficiency_and_summary_math(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        # Telemetry: Vehicle drives 100 km and consumes exactly 18 kWh of energy
        # Point 1: start
        TelemetryRecord.objects.create(
            vehicle=self.vehicle,
            timestamp=now - timedelta(hours=2),
            soc_percent=Decimal("90.0"),
            power_kw=Decimal("-25.0"),
            cumulative_energy_kwh=Decimal("50.0"),
            odometer_km=Decimal("1000.0"),
            speed_kmh=Decimal("50.0"),
        )
        # Point 2: end
        TelemetryRecord.objects.create(
            vehicle=self.vehicle,
            timestamp=now,
            soc_percent=Decimal("72.0"),
            power_kw=Decimal("-25.0"),
            cumulative_energy_kwh=Decimal("68.0"),
            odometer_km=Decimal("1100.0"),
            speed_kmh=Decimal("50.0"),
        )

        response = self.client.get(self.summary_url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["total_vehicles"] == 1
        assert Decimal(str(data["total_distance_km"])) == Decimal("100.00")
        assert Decimal(str(data["total_energy_kwh"])) == Decimal("18.000")
        # (18.0 / 100.0) * 100 = 18.00 kWh/100km
        assert Decimal(str(data["average_efficiency_kwh_per_100km"])) == Decimal("18.00")
        # Avg SOC: (90 + 72) / 2 = 81.00%
        assert Decimal(str(data["average_soc_percent"])) == Decimal("81.00")

    def test_insufficient_driving_data_returns_null_efficiency(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        # Only one point (0 distance delta)
        TelemetryRecord.objects.create(
            vehicle=self.vehicle,
            timestamp=now,
            soc_percent=Decimal("95.0"),
            power_kw=Decimal("0.0"),
            cumulative_energy_kwh=Decimal("10.0"),
            odometer_km=Decimal("1000.0"),
        )

        response = self.client.get(self.vehicle_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["distance_km"] == "0.00"
        assert response.data["realized_efficiency_kwh_per_100km"] is None