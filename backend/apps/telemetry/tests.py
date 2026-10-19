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
class TestTelemetryPipeline:
    def setup_method(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="Volt Delivery Express", slug="volt-delivery-express")
        self.user = User.objects.create_user(email="telemetry_op@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user, organization=self.org, role=Membership.RoleChoices.FLEET_OPERATOR)

        self.spec = VehicleSpecification.objects.create(
            make="VoltCargo",
            model="Van-E",
            year=2025,
            usable_battery_capacity_kwh=Decimal("80.0"),
            max_ac_charging_power_kw=Decimal("11.0"),
            max_dc_charging_power_kw=Decimal("100.0"),
            efficiency_kwh_per_100km=Decimal("22.0"),
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9TELEMETRY12345",
            license_plate="EV-TELEM-01",
            current_soc_percent=Decimal("100.0"),
            odometer_km=Decimal("500.0"),
        )
        self.batch_url = reverse("telemetry-ingest-batch")

    def test_batch_ingest_and_vehicle_state_reconciliation(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        payload = {
            "events": [
                {
                    "vehicle_id": str(self.vehicle.id),
                    "timestamp": (now - timedelta(minutes=10)).isoformat(),
                    "soc_percent": "95.00",
                    "power_kw": "-15.00",
                    "cumulative_energy_kwh": "4.000",
                    "speed_kmh": "35.00",
                    "odometer_km": "505.00",
                },
                {
                    "vehicle_id": str(self.vehicle.id),
                    "timestamp": now.isoformat(),
                    "soc_percent": "90.00",
                    "power_kw": "-20.00",
                    "cumulative_energy_kwh": "8.000",
                    "speed_kmh": "50.00",
                    "odometer_km": "512.00",
                }
            ]
        }

        response = self.client.post(self.batch_url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["accepted"] == 2
        assert response.data["ignored_duplicates"] == 0

        # Verify vehicle live state was reconciled to the latest event
        self.vehicle.refresh_from_db()
        assert self.vehicle.current_soc_percent == Decimal("90.00")
        assert self.vehicle.odometer_km == Decimal("512.00")
        assert self.vehicle.status == Vehicle.StatusChoices.IN_TRANSIT

    def test_idempotent_duplicate_handling(self):
        self.client.force_authenticate(user=self.user)
        event_time = timezone.now()

        payload = {
            "events": [
                {
                    "vehicle_id": str(self.vehicle.id),
                    "timestamp": event_time.isoformat(),
                    "soc_percent": "85.00",
                    "power_kw": "-10.00",
                    "cumulative_energy_kwh": "12.000",
                    "speed_kmh": "40.00",
                    "odometer_km": "520.00",
                }
            ]
        }

        # First ingestion
        res1 = self.client.post(self.batch_url, payload, format="json")
        assert res1.data["accepted"] == 1

        # Second identical ingestion (same vehicle + timestamp)
        res2 = self.client.post(self.batch_url, payload, format="json")
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["accepted"] == 0
        assert res2.data["ignored_duplicates"] == 1
        assert TelemetryRecord.objects.filter(vehicle=self.vehicle).count() == 1