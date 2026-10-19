from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.vehicles.models import Vehicle
from apps.telemetry.services import TelemetryIngestionService


class Command(BaseCommand):
    help = "Generates reproducible simulated telemetry points (driving and charging cycles) for fleet vehicles."

    def add_arguments(self, parser):
        parser.add_argument("--steps", type=int, default=20, help="Number of telemetry points to generate per vehicle.")
        parser.add_argument("--interval-minutes", type=int, default=5, help="Minutes between telemetry intervals.")

    def handle(self, *args, **options):
        steps = options["steps"]
        interval = options["interval_minutes"]
        now = timezone.now()

        vehicles = Vehicle.objects.filter(is_active=True).select_related("specification", "organization")
        if not vehicles.exists():
            self.stdout.write(self.style.WARNING("No active vehicles found. Please register vehicles first."))
            return

        total_ingested = 0
        for vehicle in vehicles:
            events = []
            current_soc = vehicle.current_soc_percent
            current_odo = vehicle.odometer_km
            nominal_kwh = vehicle.specification.usable_battery_capacity_kwh
            cum_energy = nominal_kwh * (Decimal("100.0") - current_soc) / Decimal("100.0")

            start_time = now - timedelta(minutes=steps * interval)

            for step in range(steps):
                event_time = start_time + timedelta(minutes=step * interval)

                # Alternate cycle: driving discharge (power < 0) vs depot charging (power > 0)
                if current_soc > Decimal("35.0"):
                    # Vehicle driving: speed ~ 45 km/h, discharge ~ -25 kW
                    speed = Decimal("45.0")
                    power = Decimal("-24.5")
                    distance_increment = (speed * Decimal(interval)) / Decimal("60.0")
                    current_odo += distance_increment
                    energy_used = abs(power) * (Decimal(interval) / Decimal("60.0"))
                    cum_energy += energy_used
                    soc_drop = (energy_used / nominal_kwh) * Decimal("100.0")
                    current_soc = max(Decimal("5.0"), current_soc - soc_drop)
                    temp = Decimal("31.5")
                else:
                    # Vehicle parked at charger: speed 0, charge ~ +50 kW
                    speed = Decimal("0.0")
                    power = Decimal("50.0")
                    energy_added = power * (Decimal(interval) / Decimal("60.0"))
                    soc_rise = (energy_added / nominal_kwh) * Decimal("100.0")
                    current_soc = min(Decimal("100.0"), current_soc + soc_rise)
                    temp = Decimal("28.0")

                events.append({
                    "vehicle_id": vehicle.id,
                    "timestamp": event_time,
                    "soc_percent": round(current_soc, 2),
                    "battery_temperature_celsius": temp,
                    "power_kw": power,
                    "cumulative_energy_kwh": round(cum_energy, 3),
                    "speed_kmh": speed,
                    "odometer_km": round(current_odo, 2),
                    "latitude": Decimal("37.774929"),
                    "longitude": Decimal("-122.419416"),
                })

            accepted, ignored = TelemetryIngestionService.ingest_batch(events, vehicle.organization)
            total_ingested += accepted
            self.stdout.write(
                f"Simulated {len(events)} events for {vehicle.license_plate} -> Accepted: {accepted}, Ignored: {ignored}"
            )

        self.stdout.write(self.style.SUCCESS(f"Telemetry simulation complete! Total records added: {total_ingested}"))