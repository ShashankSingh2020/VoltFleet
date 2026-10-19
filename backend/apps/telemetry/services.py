from decimal import Decimal
from typing import List, Dict, Any, Tuple
from django.db import transaction
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.vehicles.models import Vehicle
from .models import TelemetryRecord


class TelemetryIngestionService:
    @classmethod
    def ingest_batch(cls, records_data: List[Dict[str, Any]], organization) -> Tuple[int, int]:
        if not records_data:
            return 0, 0

        # In-batch deduplication based on (vehicle_id, timestamp)
        seen = set()
        deduped_payloads = []
        for r in records_data:
            key = (r["vehicle_id"], r["timestamp"])
            if key not in seen:
                seen.add(key)
                deduped_payloads.append(r)

        vehicle_ids = {r["vehicle_id"] for r in deduped_payloads}
        vehicles = {
            v.id: v for v in Vehicle.objects.filter(id__in=vehicle_ids, organization=organization)
        }

        records_to_create = []
        for item in deduped_payloads:
            v_id = item["vehicle_id"]
            if v_id not in vehicles:
                continue

            records_to_create.append(
                TelemetryRecord(
                    organization=organization,
                    vehicle=vehicles[v_id],
                    timestamp=item["timestamp"],
                    soc_percent=Decimal(str(item["soc_percent"])),
                    battery_temperature_celsius=Decimal(str(item["battery_temperature_celsius"])),
                    power_kw=Decimal(str(item["power_kw"])),
                    cumulative_energy_kwh=Decimal(str(item.get("cumulative_energy_kwh", "0.0"))),
                    speed_kmh=Decimal(str(item.get("speed_kmh", "0.0"))),
                    odometer_km=Decimal(str(item.get("odometer_km", "0.0"))),
                    latitude=Decimal(str(item.get("latitude", "37.7749"))),
                    longitude=Decimal(str(item.get("longitude", "-122.4194"))),
                )
            )

        with transaction.atomic():
            created_objs = TelemetryRecord.objects.bulk_create(records_to_create, ignore_conflicts=True)

            # Reconcile vehicle current state with latest telemetry
            for v_id, vehicle in vehicles.items():
                latest_record = (
                    TelemetryRecord.objects.filter(vehicle=vehicle)
                    .order_by("-timestamp")
                    .first()
                )
                if latest_record:
                    vehicle.current_soc_percent = latest_record.soc_percent
                    vehicle.odometer_km = max(vehicle.odometer_km, latest_record.odometer_km)
                    vehicle.save(update_fields=["current_soc_percent", "odometer_km", "updated_at"])

        # Broadcast live telemetry over Django Channels WebSocket Layer
        channel_layer = get_channel_layer()
        if channel_layer:
            for rec in records_to_create:
                async_to_sync(channel_layer.group_send)(
                    "fleet_telemetry_broadcast",
                    {
                        "type": "telemetry_update",
                        "data": {
                            "vehicle_id": str(rec.vehicle.id),
                            "vehicle_plate": rec.vehicle.license_plate,
                            "soc_percent": float(rec.soc_percent),
                            "battery_temperature_celsius": float(rec.battery_temperature_celsius),
                            "power_kw": float(rec.power_kw),
                            "speed_kmh": float(rec.speed_kmh),
                            "odometer_km": float(rec.odometer_km),
                            "latitude": float(rec.latitude),
                            "longitude": float(rec.longitude),
                            "timestamp": rec.timestamp.isoformat() if hasattr(rec.timestamp, "isoformat") else str(rec.timestamp),
                        },
                    },
                )

        return len(created_objs), len(records_data) - len(created_objs)
