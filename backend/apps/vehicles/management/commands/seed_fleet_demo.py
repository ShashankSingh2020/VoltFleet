from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.authentication.models import User, Organization, Membership
from apps.vehicles.models import Fleet, VehicleSpecification, Vehicle
from apps.charging.models import ChargingStation, Charger, TariffPeriod
from apps.telemetry.services import TelemetryIngestionService
from apps.anomalies.detector import AnomalyDetectionEngine
from apps.optimizer.engine import SmartChargingOptimizer
from apps.optimizer.models import ChargingPlan, ChargingPlanItem


class Command(BaseCommand):
    help = "Seeds complete portfolio-grade demo data: Organizations, Fleets, Vehicles, Telemetry, Tariffs, and Anomalies."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing VoltFleet Intelligence demonstration environment..."))

        # 1. Organizations
        apex_org, _ = Organization.objects.get_or_create(
            slug="apex-fleet",
            defaults={"name": "Apex Fleet Logistics"}
        )
        volt_org, _ = Organization.objects.get_or_create(
            slug="volt-couriers",
            defaults={"name": "Volt Express Couriers"}
        )

        # 2. Users
        admin_user, created = User.objects.get_or_create(
            email="admin@voltfleet.io",
            defaults={
                "first_name": "Chief",
                "last_name": "Dispatcher",
                "is_staff": True,
            }
        )
        if created:
            admin_user.set_password("Admin@123456")
            admin_user.save()

        Membership.objects.get_or_create(
            user=admin_user,
            organization=apex_org,
            defaults={"role": Membership.RoleChoices.ORG_ADMIN}
        )

        # 3. Vehicle Specifications
        spec_van, _ = VehicleSpecification.objects.get_or_create(
            make="VoltMotors",
            model="TransitCargo-75",
            year=2025,
            defaults={
                "usable_battery_capacity_kwh": Decimal("75.0"),
                "max_ac_charging_power_kw": Decimal("11.0"),
                "max_dc_charging_power_kw": Decimal("100.0"),
                "efficiency_kwh_per_100km": Decimal("21.5"),
            }
        )

        spec_heavy, _ = VehicleSpecification.objects.get_or_create(
            make="VoltMotors",
            model="HeavyHauler-120",
            year=2026,
            defaults={
                "usable_battery_capacity_kwh": Decimal("120.0"),
                "max_ac_charging_power_kw": Decimal("22.0"),
                "max_dc_charging_power_kw": Decimal("150.0"),
                "efficiency_kwh_per_100km": Decimal("28.0"),
            }
        )

        # 4. Fleets & Vehicles
        north_fleet, _ = Fleet.objects.get_or_create(
            organization=apex_org,
            name="North Hub Fleet",
            defaults={"depot_location": "Depot 1 - Industrial Park North"}
        )

        now = timezone.now()
        v1, _ = Vehicle.objects.get_or_create(
            vin="1V9APEX0000000001",
            defaults={
                "organization": apex_org,
                "fleet": north_fleet,
                "specification": spec_van,
                "license_plate": "APEX-EV-01",
                "nickname": "Metro Van Alpha",
                "current_soc_percent": Decimal("35.0"),
                "odometer_km": Decimal("14250.0"),
                "target_departure_time": now + timedelta(hours=6),
                "target_departure_soc_percent": Decimal("90.0"),
                "status": Vehicle.StatusChoices.AVAILABLE,
            }
        )

        v2, _ = Vehicle.objects.get_or_create(
            vin="1V9APEX0000000002",
            defaults={
                "organization": apex_org,
                "fleet": north_fleet,
                "specification": spec_heavy,
                "license_plate": "APEX-EV-02",
                "nickname": "Heavy Transport Beta",
                "current_soc_percent": Decimal("22.0"),
                "odometer_km": Decimal("28400.0"),
                "target_departure_time": now + timedelta(hours=8),
                "target_departure_soc_percent": Decimal("85.0"),
                "status": Vehicle.StatusChoices.AVAILABLE,
            }
        )

        # 5. Charging Infrastructure & Tariffs
        station, _ = ChargingStation.objects.get_or_create(
            organization=apex_org,
            name="North Depot Supercharger Hub",
            defaults={
                "location_address": "400 Terminal Way, North Industrial Hub",
                "total_grid_capacity_kw": Decimal("400.0"),
            }
        )

        charger_a, _ = Charger.objects.get_or_create(
            station=station,
            identifier="DC-FAST-01",
            defaults={
                "power_type": Charger.PowerType.DC_FAST,
                "max_output_power_kw": Decimal("150.0"),
                "efficiency_factor": Decimal("0.94"),
                "status": Charger.Status.AVAILABLE,
            }
        )

        charger_b, _ = Charger.objects.get_or_create(
            station=station,
            identifier="DC-FAST-02",
            defaults={
                "power_type": Charger.PowerType.DC_FAST,
                "max_output_power_kw": Decimal("100.0"),
                "efficiency_factor": Decimal("0.92"),
                "status": Charger.Status.AVAILABLE,
            }
        )

        TariffPeriod.objects.get_or_create(
            organization=apex_org,
            name="Off-Peak Night",
            defaults={
                "start_time": "23:00:00",
                "end_time": "07:00:00",
                "cost_per_kwh": Decimal("0.08"),
            }
        )

        TariffPeriod.objects.get_or_create(
            organization=apex_org,
            name="Standard Day",
            defaults={
                "start_time": "07:00:00",
                "end_time": "23:00:00",
                "cost_per_kwh": Decimal("0.18"),
            }
        )

        # 6. Telemetry Ingestion (with a thermal spike anomaly)
        telemetry_events = []
        for i in range(12):
            ts = now - timedelta(hours=3) + timedelta(minutes=i * 15)
            temp = Decimal("52.5") if i == 11 else Decimal("31.0") + Decimal(str(i * 0.5))
            telemetry_events.append({
                "vehicle_id": v1.id,
                "timestamp": ts,
                "soc_percent": max(Decimal("10.0"), Decimal("55.0") - Decimal(str(i * 1.8))),
                "battery_temperature_celsius": temp,
                "power_kw": Decimal("-25.0"),
                "cumulative_energy_kwh": Decimal("1500.0") + Decimal(str(i * 3.5)),
                "speed_kmh": Decimal("48.0"),
                "odometer_km": Decimal("14200.0") + Decimal(str(i * 4.2)),
                "latitude": Decimal("37.7749"),
                "longitude": Decimal("-122.4194"),
            })

        accepted, _ = TelemetryIngestionService.ingest_batch(telemetry_events, apex_org)
        self.stdout.write(f"Ingested {accepted} baseline telemetry points for APEX-EV-01.")

        # 7. Scan Anomalies
        anomalies = AnomalyDetectionEngine.scan_organization(apex_org)
        self.stdout.write(f"Detected {len(anomalies)} anomalies (including Thermal Anomaly on APEX-EV-01).")

        # 8. Generate Smart Charging Optimization Plan
        plan_result = SmartChargingOptimizer.run(
            organization=apex_org,
            horizon_start=now,
            horizon_end=now + timedelta(hours=10)
        )

        if plan_result["items"]:
            plan = ChargingPlan.objects.create(
                organization=apex_org,
                title="Automated Demonstration Schedule",
                horizon_start=now,
                horizon_end=now + timedelta(hours=10),
                status=ChargingPlan.PlanStatus.ACTIVE,
                total_vehicles_scheduled=len(plan_result["items"]),
                total_energy_kwh=plan_result["total_energy_kwh"],
                total_estimated_cost=plan_result["total_estimated_cost"],
                algorithm_metadata=plan_result["metadata"],
            )
            for item in plan_result["items"]:
                ChargingPlanItem.objects.create(
                    plan=plan,
                    vehicle=item["vehicle"],
                    charger=item["charger"],
                    scheduled_start=item["start"],
                    scheduled_end=item["end"],
                    energy_to_deliver_kwh=item["energy"],
                    estimated_cost=item["cost"],
                    target_soc_percent=item["target_soc"],
                    is_feasible=item["is_feasible"],
                    notes=item["notes"],
                )
            self.stdout.write(f"Generated Smart Charging Plan: {plan.title} (Scheduled: {plan.total_vehicles_scheduled} vehicles).")

        self.stdout.write(self.style.SUCCESS("Demo environment successfully seeded!"))
        self.stdout.write("Test Credentials:")
        self.stdout.write("  Email:    admin@voltfleet.io")
        self.stdout.write("  Password: Admin@123456")
