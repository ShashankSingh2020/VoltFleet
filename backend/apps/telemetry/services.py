from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Tuple, Optional
import logging
from django.db import transaction
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.vehicles.models import Vehicle
from .models import TelemetryRecord

logger = logging.getLogger(__name__)


def _to_decimal(val: Any) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


class TelemetryIngestionService:
    @classmethod
    def ingest_batch(cls, records_data: List[Dict[str, Any]], organization) -> Tuple[int, int]:
        if not records_data or not organization:
            return 0, 0

        # In-batch deduplication
        seen = set()
        deduped_payloads = []
        in_batch_duplicates = 0
        for r in records_data:
            v_id = r.get("vehicle_id")
            ts = r.get("timestamp")
            if not v_id or not ts:
                continue
            key = (str(v_id), str(ts))
            if key not in seen:
                seen.add(key)
                deduped_payloads.append(r)
            else:
                in_batch_duplicates += 1

        vehicle_ids = {r["vehicle_id"] for r in deduped_payloads}
        vehicles = {
            str(v.id): v
            for v in Vehicle.objects.filter(id__in=vehicle_ids, organization=organization)
        }

        # Check existing records in DB to detect exact duplicates
        existing_keys = set()
        if deduped_payloads:
            q_filter = Q()
            for r in deduped_payloads:
                if str(r.get("vehicle_id")) in vehicles:
                    q_filter |= Q(vehicle_id=r["vehicle_id"], timestamp=r["timestamp"])
            if q_filter:
                existing_keys = {
                    (str(rec.vehicle_id), rec.timestamp.isoformat() if hasattr(rec.timestamp, "isoformat") else str(rec.timestamp))
                    for rec in TelemetryRecord.objects.filter(q_filter)
                }

        records_to_create = []
        db_duplicates = 0
        for item in deduped_payloads:
            v_id = str(item.get("vehicle_id"))
            vehicle = vehicles.get(v_id)
            if not vehicle:
                continue

            ts_str = item["timestamp"].isoformat() if hasattr(item["timestamp"], "isoformat") else str(item["timestamp"])
            if (v_id, ts_str) in existing_keys:
                db_duplicates += 1
                continue

            soc = _to_decimal(item.get("soc_percent"))
            if soc is None:
                continue

            records_to_create.append(
                TelemetryRecord(
                    vehicle=vehicle,
                    timestamp=item["timestamp"],
                    soc_percent=soc,
                    battery_temperature_celsius=_to_decimal(item.get("battery_temperature_celsius")),
                    power_kw=_to_decimal(item.get("power_kw")) or Decimal("0.0"),
                    cumulative_energy_kwh=_to_decimal(item.get("cumulative_energy_kwh")) or Decimal("0.0"),
                    speed_kmh=_to_decimal(item.get("speed_kmh")) or Decimal("0.0"),
                    odometer_km=_to_decimal(item.get("odometer_km")) or Decimal("0.0"),
                    latitude=_to_decimal(item.get("latitude")),
                    longitude=_to_decimal(item.get("longitude")),
                )
            )

        total_duplicates = in_batch_duplicates + db_duplicates

        if not records_to_create:
            return 0, total_duplicates

        with transaction.atomic():
            created_objs = TelemetryRecord.objects.bulk_create(records_to_create, ignore_conflicts=True)

            # Reconcile vehicle state to the latest telemetry record
            for v_id, vehicle in vehicles.items():
                latest_record = (
                    TelemetryRecord.objects.filter(vehicle=vehicle)
                    .order_by("-timestamp")
                    .first()
                )
                if latest_record:
                    fields_to_update = ["updated_at"]
                    if latest_record.soc_percent is not None:
                        vehicle.current_soc_percent = latest_record.soc_percent
                        fields_to_update.append("current_soc_percent")
                    if latest_record.odometer_km is not None and latest_record.odometer_km > vehicle.odometer_km:
                        vehicle.odometer_km = latest_record.odometer_km
                        fields_to_update.append("odometer_km")

                    # Reconcile status based on speed / motion
                    if latest_record.speed_kmh is not None and latest_record.speed_kmh > Decimal("0.0"):
                        if vehicle.status != Vehicle.StatusChoices.IN_TRANSIT:
                            vehicle.status = Vehicle.StatusChoices.IN_TRANSIT
                            fields_to_update.append("status")

                    vehicle.save(update_fields=fields_to_update)

        channel_layer = get_channel_layer()
        if channel_layer:
            org_group = f"fleet_telemetry_{str(organization.id)}"
            for rec in created_objs:
                try:
                    async_to_sync(channel_layer.group_send)(
                        org_group,
                        {
                            "type": "telemetry_update",
                            "data": {
                                "vehicle_id": str(rec.vehicle.id),
                                "vehicle_plate": rec.vehicle.license_plate,
                                "soc_percent": float(rec.soc_percent) if rec.soc_percent is not None else None,
                                "battery_temperature_celsius": float(rec.battery_temperature_celsius) if rec.battery_temperature_celsius is not None else None,
                                "power_kw": float(rec.power_kw) if rec.power_kw is not None else 0.0,
                                "speed_kmh": float(rec.speed_kmh) if rec.speed_kmh is not None else 0.0,
                                "odometer_km": float(rec.odometer_km) if rec.odometer_km is not None else 0.0,
                                "latitude": float(rec.latitude) if rec.latitude is not None else None,
                                "longitude": float(rec.longitude) if rec.longitude is not None else None,
                                "timestamp": rec.timestamp.isoformat() if hasattr(rec.timestamp, "isoformat") else str(rec.timestamp),
                            },
                        },
                    )
                except Exception as exc:
                    logger.warning("WebSocket broadcast error: %s", exc)

        return len(created_objs), total_duplicates
