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
from apps.anomalies.models import Anomaly
from apps.anomalies.detector import AnomalyDetectionEngine


@pytest.mark.django_db
class TestAnomalyDetection:
    def setup_method(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="SafeFleet Telematics", slug="safefleet-telematics")
        self.user = User.objects.create_user(email="safety_op@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user, organization=self.org, role=Membership.RoleChoices.FLEET_OPERATOR)

        self.spec = VehicleSpecification.objects.create(
            make="VoltSafety",
            model="ShieldVan",
            year=2025,
            usable_battery_capacity_kwh=Decimal("80.0"),
            max_ac_charging_power_kw=Decimal("11.0"),
            max_dc_charging_power_kw=Decimal("100.0"),
            efficiency_kwh_per_100km=Decimal("20.0"),
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9ANOMALY1234567",
            license_plate="EV-ANOM-01",
            current_soc_percent=Decimal("60.0"),
            odometer_km=Decimal("2000.0"),
        )

    def test_detects_high_battery_temperature_and_suppresses_duplicates(self):
        now = timezone.now()
        # Telemetry record with dangerous 51.5 °C battery core temp
        TelemetryRecord.objects.create(
            vehicle=self.vehicle,
            timestamp=now,
            soc_percent=Decimal("50.0"),
            battery_temperature_celsius=Decimal("51.5"),
            power_kw=Decimal("-30.0"),
            cumulative_energy_kwh=Decimal("100.0"),
            odometer_km=Decimal("2010.0"),
        )

        # Run 1: Should detect 1 CRITICAL anomaly
        detected_run1 = AnomalyDetectionEngine.scan_organization(self.org)
        assert len(detected_run1) == 1
        anomaly = detected_run1[0]
        assert anomaly.anomaly_type == Anomaly.AnomalyType.HIGH_BATTERY_TEMP
        assert anomaly.severity == Anomaly.Severity.CRITICAL
        assert anomaly.status == Anomaly.Status.OPEN

        # Run 2 immediately after: Alert suppression cooldown must prevent duplicate alert
        detected_run2 = AnomalyDetectionEngine.scan_organization(self.org)
        assert len(detected_run2) == 0
        assert Anomaly.objects.filter(vehicle=self.vehicle).count() == 1

    def test_detects_sudden_soc_drop(self):
        now = timezone.now()
        # Point 1: 5 minutes ago at 80% SOC
        TelemetryRecord.objects.create(
            vehicle=self.vehicle,
            timestamp=now - timedelta(minutes=5),
            soc_percent=Decimal("80.0"),
            power_kw=Decimal("-10.0"),
            cumulative_energy_kwh=Decimal("50.0"),
            odometer_km=Decimal("2000.0"),
        )
        # Point 2: Now at 70% SOC (10% drop in 5 mins across only 0.5 km)
        TelemetryRecord.objects.create(
            vehicle=self.vehicle,
            timestamp=now,
            soc_percent=Decimal("70.0"),
            power_kw=Decimal("-10.0"),
            cumulative_energy_kwh=Decimal("50.5"),
            odometer_km=Decimal("2000.5"),
        )

        detected = AnomalyDetectionEngine.scan_organization(self.org)
        assert len(detected) == 1
        assert detected[0].anomaly_type == Anomaly.AnomalyType.SUDDEN_SOC_DROP
        assert detected[0].severity == Anomaly.Severity.HIGH

    def test_anomaly_resolution_workflow_api(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        anomaly = Anomaly.objects.create(
            organization=self.org,
            vehicle=self.vehicle,
            anomaly_type=Anomaly.AnomalyType.HIGH_BATTERY_TEMP,
            severity=Anomaly.Severity.CRITICAL,
            detected_at=now,
            observed_value="52.0 °C",
            threshold_value="> 45.0 °C",
            evidence_summary="Extreme temperature detected.",
        )

        ack_url = reverse("anomaly-acknowledge", kwargs={"pk": anomaly.id})
        res_ack = self.client.post(ack_url, {"notes": "Inspecting thermal cooling system"})
        assert res_ack.status_code == status.HTTP_200_OK
        assert res_ack.data["status"] == "ACKNOWLEDGED"

        resolve_url = reverse("anomaly-resolve", kwargs={"pk": anomaly.id})
        res_resolve = self.client.post(resolve_url, {"notes": "Coolant pump replaced"})
        assert res_resolve.status_code == status.HTTP_200_OK
        assert res_resolve.data["status"] == "RESOLVED"
        assert len(res_resolve.data["resolution_logs"]) == 2