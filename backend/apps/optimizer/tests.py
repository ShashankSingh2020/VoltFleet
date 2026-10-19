from decimal import Decimal
from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import User, Organization, Membership
from apps.vehicles.models import Vehicle, VehicleSpecification
from apps.charging.models import ChargingStation, Charger, TariffPeriod
from apps.optimizer.models import ChargingPlan


@pytest.mark.django_db
class TestSmartChargingOptimizer:
    def setup_method(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="OptiFleet Energy", slug="optifleet-energy")
        self.user = User.objects.create_user(email="optimizer_op@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user, organization=self.org, role=Membership.RoleChoices.FLEET_OPERATOR)

        # 100 kWh battery, 50 kW max DC charge
        self.spec = VehicleSpecification.objects.create(
            make="VoltTruck",
            model="Hauler",
            year=2025,
            usable_battery_capacity_kwh=Decimal("100.0"),
            max_ac_charging_power_kw=Decimal("22.0"),
            max_dc_charging_power_kw=Decimal("50.0"),
            efficiency_kwh_per_100km=Decimal("25.0"),
        )
        self.station = ChargingStation.objects.create(
            organization=self.org,
            name="Depot Alpha",
            total_grid_capacity_kw=Decimal("200.0"),
        )
        # 50 kW charger, 100% efficiency for simple math
        self.charger = Charger.objects.create(
            station=self.station,
            identifier="DC-50-A",
            power_type=Charger.PowerType.DC_FAST,
            max_output_power_kw=Decimal("50.0"),
            efficiency_factor=Decimal("1.0"),
        )

        # Tariff: .10/kWh
        TariffPeriod.objects.create(
            organization=self.org,
            name="Standard",
            start_time="00:00:00",
            end_time="23:59:59",
            cost_per_kwh=Decimal("0.10"),
        )
        self.generate_url = reverse("charging-plan-generate-plan")

    def test_single_vehicle_feasible_optimization(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        # Vehicle at 50% SOC, needs 80% SOC -> 30 kWh required
        # At 50 kW power, 30 kWh takes 36 minutes -> rounded to 45 mins (3 slots)
        vehicle = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9OPTIMIZE123456",
            license_plate="EV-OPTI-01",
            current_soc_percent=Decimal("50.0"),
            target_departure_soc_percent=Decimal("80.0"),
            target_departure_time=now + timedelta(hours=4),
        )

        payload = {
            "title": "Morning Schedule",
            "horizon_start": now.isoformat(),
            "horizon_end": (now + timedelta(hours=6)).isoformat(),
        }

        response = self.client.post(self.generate_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data

        assert data["total_vehicles_scheduled"] == 1
        assert Decimal(str(data["total_energy_kwh"])) == Decimal("30.000")
        # 30 kWh * .10 = .00
        assert Decimal(str(data["total_estimated_cost"])) == Decimal("3.00")
        assert len(data["items"]) == 1
        assert data["items"][0]["is_feasible"] is True

    def test_competing_vehicles_sequential_scheduling(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        # Vehicle 1 departs in 2 hours
        v1 = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9COMPETE1111111",
            license_plate="EV-EARLY",
            current_soc_percent=Decimal("50.0"),
            target_departure_soc_percent=Decimal("80.0"),
            target_departure_time=now + timedelta(hours=2),
        )
        # Vehicle 2 departs in 5 hours
        v2 = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9COMPETE2222222",
            license_plate="EV-LATER",
            current_soc_percent=Decimal("50.0"),
            target_departure_soc_percent=Decimal("80.0"),
            target_departure_time=now + timedelta(hours=5),
        )

        payload = {
            "title": "Two-Vehicle Sequential",
            "horizon_start": now.isoformat(),
            "horizon_end": (now + timedelta(hours=6)).isoformat(),
        }

        response = self.client.post(self.generate_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.data

        assert data["total_vehicles_scheduled"] == 2
        items = data["items"]
        # Earlier deadline vehicle scheduled first
        assert items[0]["vehicle_plate"] == "EV-EARLY"
        assert items[1]["vehicle_plate"] == "EV-LATER"
        # Item 2 start must be >= Item 1 end (no collision on charger)
        assert items[1]["scheduled_start"] >= items[0]["scheduled_end"]