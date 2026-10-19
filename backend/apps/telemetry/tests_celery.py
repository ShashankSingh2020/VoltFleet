import uuid
from decimal import Decimal
from datetime import timedelta
import pytest
from django.utils import timezone
from apps.authentication.models import Organization
from apps.vehicles.models import Vehicle, VehicleSpecification
from apps.telemetry.models import TelemetryRecord
from apps.telemetry.tasks import process_telemetry_batch_async
from apps.anomalies.tasks import run_scheduled_anomaly_scans
from apps.anomalies.models import Anomaly


@pytest.mark.django_db(transaction=True)
class TestCeleryBackgroundTasks:
    def setup_method(self):
        self.org = Organization.objects.create(name="Celery Fleet Hub", slug="celery-fleet-hub")
        self.spec = VehicleSpecification.objects.create(
            make="VoltCargo",
            model="AsyncVan",
            year=2025,
            usable_battery_capacity_kwh=Decimal("80.0"),
            max_ac_charging_power_kw=Decimal("11.0"),
            max_dc_charging_power_kw=Decimal("100.0"),
            efficiency_kwh_per_100km=Decimal("20.0"),
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9CELERY12345678",
            license_plate="EV-CELERY-01",
            current_soc_percent=Decimal("75.0"),
            odometer_km=Decimal("3000.0"),
        )

    def test_process_telemetry_batch_async_task(self):
        now = timezone.now()
        payload = [
            {
                "vehicle_id": str(self.vehicle.id),
                "timestamp": now.isoformat(),
                "soc_percent": "70.00",
                "battery_temperature_celsius": "32.00",
                "power_kw": "-20.00",
                "cumulative_energy_kwh": "45.000",
                "speed_kmh": "45.00",
                "odometer_km": "3015.00",
            }
        ]

        result = process_telemetry_batch_async.apply(args=[payload, str(self.org.id)])
        task_output = result.get()

        assert task_output["status"] == "success"
        assert task_output["accepted"] == 1
        assert task_output["ignored"] == 0

        self.vehicle.refresh_from_db()
        assert self.vehicle.current_soc_percent == Decimal("70.00")
        assert self.vehicle.odometer_km == Decimal("3015.00")

    def test_run_scheduled_anomaly_scans_task(self):
        now = timezone.now()
        TelemetryRecord.objects.create(
            vehicle=self.vehicle,
            timestamp=now,
            soc_percent=Decimal("65.0"),
            battery_temperature_celsius=Decimal("52.0"),
            power_kw=Decimal("-30.0"),
            cumulative_energy_kwh=Decimal("60.0"),
            odometer_km=Decimal("3050.0"),
        )

        result = run_scheduled_anomaly_scans.apply()
        task_output = result.get()

        assert task_output["status"] == "completed"
        assert task_output["organizations_scanned"] >= 1
        assert task_output["new_anomalies_detected"] == 1
        assert Anomaly.objects.filter(vehicle=self.vehicle, severity=Anomaly.Severity.CRITICAL).count() == 1