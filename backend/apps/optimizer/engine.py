from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from django.utils import timezone
from apps.vehicles.models import Vehicle
from apps.charging.models import Charger, TariffPeriod


class SmartChargingOptimizer:
    SLOT_MINUTES = 15

    @classmethod
    def run(
        cls,
        organization,
        horizon_start: datetime,
        horizon_end: datetime,
        vehicle_ids: List[str] = None,
        charger_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a deterministic slot-based smart charging optimization run.
        """
        # Fetch candidate vehicles needing charge
        vehicles_qs = Vehicle.objects.filter(
            organization=organization,
            is_active=True,
            status__in=[Vehicle.StatusChoices.AVAILABLE, Vehicle.StatusChoices.CHARGING]
        ).select_related("specification")
        if vehicle_ids:
            vehicles_qs = vehicles_qs.filter(id__in=vehicle_ids)

        chargers_qs = Charger.objects.filter(
            station__organization=organization,
            status__in=[Charger.Status.AVAILABLE, Charger.Status.OCCUPIED]
        ).select_related("station")
        if charger_ids:
            chargers_qs = chargers_qs.filter(id__in=charger_ids)

        tariffs = list(TariffPeriod.objects.filter(organization=organization, is_active=True))

        plan_items = []
        total_energy = Decimal("0.0")
        total_cost = Decimal("0.0")
        unmet_vehicles = []

        # Track occupied time windows per charger: charger_id -> List[Tuple[start, end]]
        charger_reservations: Dict[Any, List[Tuple[datetime, datetime]]] = {
            c.id: [] for c in chargers_qs
        }

        # Sort vehicles by urgency: departure deadline first, then lower current SOC
        candidate_vehicles = list(vehicles_qs)
        fallback_deadline = horizon_end

        def sort_key(v: Vehicle):
            deadline = v.target_departure_time if v.target_departure_time else fallback_deadline
            return (deadline, v.current_soc_percent)

        candidate_vehicles.sort(key=sort_key)

        for vehicle in candidate_vehicles:
            target_soc = vehicle.target_departure_soc_percent
            current_soc = vehicle.current_soc_percent

            # If already at or above target, no charge required
            if current_soc >= target_soc:
                continue

            capacity_kwh = vehicle.specification.usable_battery_capacity_kwh
            soc_delta = target_soc - current_soc
            required_energy = capacity_kwh * (soc_delta / Decimal("100.0"))

            departure_deadline = vehicle.target_departure_time or horizon_end
            if departure_deadline > horizon_end:
                departure_deadline = horizon_end

            # Determine vehicle max allowable power
            vehicle_max_pwr = (
                vehicle.specification.max_dc_charging_power_kw
                if vehicle.specification.max_dc_charging_power_kw > Decimal("0.0")
                else vehicle.specification.max_ac_charging_power_kw
            )

            # Find best feasible charger and slot window
            best_allocation = None
            lowest_allocation_cost = Decimal("999999.0")

            for charger in chargers_qs:
                effective_pwr = min(charger.max_output_power_kw, vehicle_max_pwr)
                efficiency = charger.efficiency_factor
                duration_hours = required_energy / (effective_pwr * efficiency)
                duration_minutes = int(Decimal.from_float(float(duration_hours * 60)).quantize(Decimal("1")))

                if duration_minutes < cls.SLOT_MINUTES:
                    duration_minutes = cls.SLOT_MINUTES

                # Align to slot increments
                rem = duration_minutes % cls.SLOT_MINUTES
                if rem != 0:
                    duration_minutes += (cls.SLOT_MINUTES - rem)

                req_duration = timedelta(minutes=duration_minutes)

                # Search for available start window between horizon_start and departure_deadline
                curr_start = horizon_start
                while curr_start + req_duration <= departure_deadline:
                    curr_end = curr_start + req_duration

                    # Verify no collision with existing reservations on this charger
                    has_collision = False
                    for r_start, r_end in charger_reservations[charger.id]:
                        if max(curr_start, r_start) < min(curr_end, r_end):
                            has_collision = True
                            break

                    if not has_collision:
                        # Calculate cost based on tariff periods
                        cost = cls._calculate_cost(curr_start, curr_end, required_energy, tariffs)
                        if cost < lowest_allocation_cost:
                            lowest_allocation_cost = cost
                            best_allocation = {
                                "vehicle": vehicle,
                                "charger": charger,
                                "start": curr_start,
                                "end": curr_end,
                                "energy": round(required_energy, 3),
                                "cost": round(cost, 2),
                                "target_soc": target_soc,
                                "is_feasible": True,
                                "notes": f"Scheduled at {effective_pwr} kW with efficiency {efficiency}."
                            }
                    curr_start += timedelta(minutes=cls.SLOT_MINUTES)

            if best_allocation:
                plan_items.append(best_allocation)
                charger_reservations[best_allocation["charger"].id].append(
                    (best_allocation["start"], best_allocation["end"])
                )
                total_energy += best_allocation["energy"]
                total_cost += best_allocation["cost"]
            else:
                unmet_vehicles.append({
                    "vehicle_id": str(vehicle.id),
                    "license_plate": vehicle.license_plate,
                    "reason": "Insufficient charger capacity or time before departure deadline."
                })

        return {
            "items": plan_items,
            "total_energy_kwh": total_energy,
            "total_estimated_cost": total_cost,
            "unmet_vehicles": unmet_vehicles,
            "metadata": {
                "algorithm": "Earliest-Deadline-First TOU Slot Optimizer",
                "slot_granularity_minutes": cls.SLOT_MINUTES,
                "chargers_evaluated": chargers_qs.count(),
                "vehicles_evaluated": len(candidate_vehicles),
            }
        }

    @classmethod
    def _calculate_cost(
        cls,
        start: datetime,
        end: datetime,
        energy_kwh: Decimal,
        tariffs: List[TariffPeriod]
    ) -> Decimal:
        """
        Estimates electricity charging cost against active tariff windows.
        Falls back to default rate if tariffs are not specified.
        """
        if not tariffs:
            return energy_kwh * Decimal("0.18")  # Flat fallback rate: .18/kWh

        avg_rate = Decimal("0.0")
        matched = 0
        midpoint_time = (start + (end - start) / 2).time()

        for tariff in tariffs:
            if tariff.start_time <= tariff.end_time:
                if tariff.start_time <= midpoint_time <= tariff.end_time:
                    return energy_kwh * tariff.cost_per_kwh
            else:
                # Overnight tariff spanning midnight (e.g. 22:00 to 06:00)
                if midpoint_time >= tariff.start_time or midpoint_time <= tariff.end_time:
                    return energy_kwh * tariff.cost_per_kwh

        return energy_kwh * tariffs[0].cost_per_kwh