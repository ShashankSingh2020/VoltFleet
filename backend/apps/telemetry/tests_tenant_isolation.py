import pytest
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient
from apps.authentication.models import User, Organization, Membership
from apps.vehicles.models import Vehicle, VehicleSpecification
from apps.telemetry.models import TelemetryRecord
from apps.telemetry.services import TelemetryIngestionService


@pytest.mark.django_db
class TestTenantIsolation:
    @pytest.fixture(autouse=True)
    def setup_tenants(self):
        self.org_a = Organization.objects.create(name="Apex Fleet", slug="apex-fleet")
        self.org_b = Organization.objects.create(name="Volt Express", slug="volt-express")

        self.user_a = User.objects.create_user(
            email="user_a@apex.com", password="Password123!"
        )
        Membership.objects.create(
            user=self.user_a,
            organization=self.org_a,
            role=Membership.RoleChoices.FLEET_OPERATOR,
        )

        self.user_b = User.objects.create_user(
            email="user_b@volt.com", password="Password123!"
        )
        Membership.objects.create(
            user=self.user_b,
            organization=self.org_b,
            role=Membership.RoleChoices.FLEET_OPERATOR,
        )

        self.spec = VehicleSpecification.objects.create(
            make="VoltCargo",
            model="Van-E",
            year=2025,
            usable_battery_capacity_kwh=Decimal("100.0"),
            max_ac_charging_power_kw=Decimal("22.0"),
            max_dc_charging_power_kw=Decimal("150.0"),
            efficiency_kwh_per_100km=Decimal("20.0"),
        )

        self.vehicle_a = Vehicle.objects.create(
            organization=self.org_a,
            specification=self.spec,
            vin="1V9APEX00000000A1",
            license_plate="APEX-A1",
            current_soc_percent=Decimal("100.0"),
            odometer_km=Decimal("100.0"),
        )
        self.vehicle_b = Vehicle.objects.create(
            organization=self.org_b,
            specification=self.spec,
            vin="1V9VOLT00000000B1",
            license_plate="VOLT-B1",
            current_soc_percent=Decimal("100.0"),
            odometer_km=Decimal("100.0"),
        )

        self.client_a = APIClient()
        self.client_a.force_authenticate(user=self.user_a)

        self.client_b = APIClient()
        self.client_b.force_authenticate(user=self.user_b)

    def test_user_cannot_view_other_tenant_telemetry(self):
        TelemetryRecord.objects.create(
            vehicle=self.vehicle_b,
            timestamp=timezone.now(),
            soc_percent=Decimal("50.0"),
            battery_temperature_celsius=Decimal("30.0"),
            power_kw=Decimal("0.0"),
            cumulative_energy_kwh=Decimal("0.0"),
            speed_kmh=Decimal("0.0"),
            odometer_km=Decimal("100.0"),
        )

        res = self.client_a.get("/api/v1/telemetry/history/")
        assert res.status_code == 200
        results = res.data.get("results", res.data)
        assert len(results) == 0

        res_b = self.client_b.get("/api/v1/telemetry/history/")
        assert res_b.status_code == 200
        results_b = res_b.data.get("results", res_b.data)
        assert len(results_b) == 1
        assert str(results_b[0]["vehicle"]) == str(self.vehicle_b.id)

    def test_ingestion_rejects_cross_tenant_spoofing(self):
        payload = [
            {
                "vehicle_id": str(self.vehicle_b.id),
                "timestamp": timezone.now().isoformat(),
                "soc_percent": "75.0",
                "battery_temperature_celsius": "35.0",
                "cumulative_energy_kwh": "10.0",
            }
        ]

        created, deduped = TelemetryIngestionService.ingest_batch(payload, organization=self.org_a)
        assert created == 0

    def test_missing_and_none_fields_handling(self):
        payload = [
            {
                "vehicle_id": str(self.vehicle_a.id),
                "timestamp": timezone.now().isoformat(),
                "soc_percent": "80.0",
                "battery_temperature_celsius": None,
                "latitude": None,
                "longitude": None,
            }
        ]

        created, _ = TelemetryIngestionService.ingest_batch(payload, organization=self.org_a)
        assert created == 1
        rec = TelemetryRecord.objects.filter(vehicle=self.vehicle_a).first()
        assert rec.soc_percent == Decimal("80.0")
        assert rec.battery_temperature_celsius is None
        assert rec.latitude is None
