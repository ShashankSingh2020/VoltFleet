from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db.models import Min, Max, Avg, Count
from apps.vehicles.models import Vehicle
from apps.telemetry.models import TelemetryRecord


class FleetAnalyticsService:
    @staticmethod
    def get_fleet_summary(organization, start_time=None, end_time=None, fleet_id=None) -> Dict[str, Any]:
        """
        Calculates high-level aggregated operational metrics for an organization's fleet:
        - Active vehicle count
        - Real-time vehicle status distribution
        - Total distance travelled (km)
        - Net energy consumed (kWh)
        - Average fleet-wide efficiency (kWh/100km)
        - Average recorded SOC (%)
        """
        vehicles_qs = Vehicle.objects.filter(organization=organization, is_active=True)
        if fleet_id:
            vehicles_qs = vehicles_qs.filter(fleet_id=fleet_id)

        total_vehicles = vehicles_qs.count()
        if total_vehicles == 0:
            return {
                "total_vehicles": 0,
                "status_breakdown": {},
                "total_distance_km": Decimal("0.0"),
                "total_energy_kwh": Decimal("0.0"),
                "average_efficiency_kwh_per_100km": None,
                "average_soc_percent": None,
            }

        # Status distribution breakdown
        status_counts = vehicles_qs.values("status").annotate(count=Count("status"))
        status_breakdown = {item["status"]: item["count"] for item in status_counts}

        # Scope telemetry records to this organization's active vehicles
        telemetry_qs = TelemetryRecord.objects.filter(vehicle__in=vehicles_qs)
        if start_time:
            telemetry_qs = telemetry_qs.filter(timestamp__gte=start_time)
        if end_time:
            telemetry_qs = telemetry_qs.filter(timestamp__lte=end_time)

        # Aggregate telemetry metrics per vehicle to accurately compute delta distance and delta energy
        per_vehicle_stats = telemetry_qs.values("vehicle_id").annotate(
            min_odo=Min("odometer_km"),
            max_odo=Max("odometer_km"),
            min_energy=Min("cumulative_energy_kwh"),
            max_energy=Max("cumulative_energy_kwh"),
            avg_soc=Avg("soc_percent")
        )

        total_distance = Decimal("0.0")
        total_energy = Decimal("0.0")
        soc_accum = Decimal("0.0")
        vehicles_with_telemetry = 0

        for stat in per_vehicle_stats:
            if stat["min_odo"] is not None and stat["max_odo"] is not None:
                dist = stat["max_odo"] - stat["min_odo"]
                if dist > Decimal("0.0"):
                    total_distance += dist

            if stat["min_energy"] is not None and stat["max_energy"] is not None:
                energy = stat["max_energy"] - stat["min_energy"]
                if energy > Decimal("0.0"):
                    total_energy += energy

            if stat["avg_soc"] is not None:
                soc_accum += Decimal(str(stat["avg_soc"]))
                vehicles_with_telemetry += 1

        avg_soc = (
            round(soc_accum / Decimal(vehicles_with_telemetry), 2)
            if vehicles_with_telemetry > 0
            else None
        )

        # Calculate realized efficiency: (total_energy / total_distance) * 100
        # If distance < 1.0 km, return None to signify insufficient driving data
        if total_distance >= Decimal("1.0"):
            efficiency = round((total_energy / total_distance) * Decimal("100.0"), 2)
        else:
            efficiency = None

        return {
            "total_vehicles": total_vehicles,
            "status_breakdown": status_breakdown,
            "total_distance_km": round(total_distance, 2),
            "total_energy_kwh": round(total_energy, 3),
            "average_efficiency_kwh_per_100km": efficiency,
            "average_soc_percent": avg_soc,
        }

    @staticmethod
    def get_vehicle_efficiency(vehicle, start_time=None, end_time=None) -> Dict[str, Any]:
        """
        Calculates interval metrics for a single specific vehicle.
        """
        records = TelemetryRecord.objects.filter(vehicle=vehicle)
        if start_time:
            records = records.filter(timestamp__gte=start_time)
        if end_time:
            records = records.filter(timestamp__lte=end_time)

        aggregates = records.aggregate(
            min_odo=Min("odometer_km"),
            max_odo=Max("odometer_km"),
            min_energy=Min("cumulative_energy_kwh"),
            max_energy=Max("cumulative_energy_kwh"),
            avg_soc=Avg("soc_percent"),
            avg_temp=Avg("battery_temperature_celsius"),
        )

        min_odo = aggregates["min_odo"]
        max_odo = aggregates["max_odo"]
        min_energy = aggregates["min_energy"]
        max_energy = aggregates["max_energy"]

        if min_odo is None or max_odo is None or min_energy is None or max_energy is None:
            return {
                "vehicle_id": vehicle.id,
                "license_plate": vehicle.license_plate,
                "distance_km": Decimal("0.0"),
                "energy_consumed_kwh": Decimal("0.0"),
                "realized_efficiency_kwh_per_100km": None,
                "average_soc_percent": None,
                "average_battery_temp_celsius": None,
                "data_points_analyzed": 0,
            }

        distance = max_odo - min_odo
        energy = max_energy - min_energy

        efficiency = (
            round((energy / distance) * Decimal("100.0"), 2)
            if distance >= Decimal("1.0")
            else None
        )

        avg_soc = round(Decimal(str(aggregates["avg_soc"])), 2) if aggregates["avg_soc"] is not None else None
        avg_temp = round(Decimal(str(aggregates["avg_temp"])), 2) if aggregates["avg_temp"] is not None else None

        return {
            "vehicle_id": vehicle.id,
            "license_plate": vehicle.license_plate,
            "distance_km": round(distance, 2),
            "energy_consumed_kwh": round(energy, 3),
            "realized_efficiency_kwh_per_100km": efficiency,
            "average_soc_percent": avg_soc,
            "average_battery_temp_celsius": avg_temp,
            "data_points_analyzed": records.count(),
        }