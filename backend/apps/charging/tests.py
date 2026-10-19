from decimal import Decimal
from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import User, Organization, Membership
from apps.vehicles.models import Vehicle, VehicleSpecification
from apps.charging.models import ChargingStation, Charger, TariffPeriod, ChargingSession


@pytest.mark.django_db
class TestChargingInfrastructureAPI:
    def setup_method(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="Volt Depot Hub", slug="volt-depot-hub")
        self.user = User.objects.create_user(email="depot_op@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user, organization=self.org, role=Membership.RoleChoices.FLEET_OPERATOR)

        # Vehicle
        self.spec = VehicleSpecification.objects.create(
            make="VoltTransit",
            model="ProVan",
            year=2025,
            usable_battery_capacity_kwh=Decimal("90.0"),
            max_ac_charging_power_kw=Decimal("22.0"),
            max_dc_charging_power_kw=Decimal("150.0"),
            efficiency_kwh_per_100km=Decimal("21.0"),
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9CHARGING123456",
            license_plate="EV-CHARGE-01",
            current_soc_percent=Decimal("20.0"),
            odometer_km=Decimal("1200.0"),
        )

        # Station & Charger
        self.station = ChargingStation.objects.create(
            organization=self.org,
            name="Main Depot",
            total_grid_capacity_kw=Decimal("500.0"),
        )
        self.charger = Charger.objects.create(
            station=self.station,
            identifier="DC-FAST-01",
            power_type=Charger.PowerType.DC_FAST,
            max_output_power_kw=Decimal("120.0"),
            efficiency_factor=Decimal("0.95"),
        )
        self.sessions_url = reverse("charging-session-list")

    def test_create_valid_charging_session(self):
        self.client.force_authenticate(user=self.user)
        start = timezone.now()
        end = start + timedelta(hours=1)

        payload = {
            "charger": str(self.charger.id),
            "vehicle": str(self.vehicle.id),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "initial_soc_percent": "20.00",
            "final_soc_percent": "85.00",
            "energy_delivered_kwh": "58.500",
            "total_cost": "11.70",
            "status": "COMPLETED",
        }

        response = self.client.post(self.sessions_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "COMPLETED"
        assert Decimal(response.data["energy_delivered_kwh"]) == Decimal("58.500")

    def test_prevent_overlapping_sessions_on_same_charger(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        # Existing active/in-progress session from 10:00 to 11:30
        ChargingSession.objects.create(
            charger=self.charger,
            vehicle=self.vehicle,
            start_time=now,
            end_time=now + timedelta(minutes=90),
            initial_soc_percent=Decimal("15.0"),
            status=ChargingSession.SessionStatus.IN_PROGRESS,
        )

        # Attempt to schedule second session overlapping between 10:30 and 11:00
        conflict_payload = {
            "charger": str(self.charger.id),
            "vehicle": str(self.vehicle.id),
            "start_time": (now + timedelta(minutes=30)).isoformat(),
            "end_time": (now + timedelta(minutes=60)).isoformat(),
            "initial_soc_percent": "30.00",
            "status": "IN_PROGRESS",
        }

        response = self.client.post(self.sessions_url, conflict_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "charger" in response.data

    def test_reject_impossible_soc_drop_during_charging(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        invalid_payload = {
            "charger": str(self.charger.id),
            "vehicle": str(self.vehicle.id),
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "initial_soc_percent": "60.00",
            "final_soc_percent": "40.00",  # Impossible: SOC cannot drop during charging session
            "status": "COMPLETED",
        }

        response = self.client.post(self.sessions_url, invalid_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "final_soc_percent" in response.data