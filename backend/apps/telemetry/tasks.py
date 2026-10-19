import uuid
import logging
from celery import shared_task
from decimal import Decimal
from django.utils.dateparse import parse_datetime
from apps.authentication.models import Organization
from apps.telemetry.services import TelemetryIngestionService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_telemetry_batch_async(self, events_data: list, organization_id: str):
    """
    Celery background worker task for ingesting telemetry batches.
    Converts serialized values into UUIDs, Decimals, and Datetimes before service execution.
    """
    try:
        org_id = uuid.UUID(str(organization_id)) if not isinstance(organization_id, uuid.UUID) else organization_id
        org = Organization.objects.get(id=org_id)

        parsed_events = []
        for event in events_data:
            raw_ts = event["timestamp"]
            ts = parse_datetime(raw_ts) if isinstance(raw_ts, str) else raw_ts

            vid_raw = event["vehicle_id"]
            vid = uuid.UUID(str(vid_raw)) if not isinstance(vid_raw, uuid.UUID) else vid_raw

            parsed_events.append({
                "vehicle_id": vid,
                "timestamp": ts,
                "soc_percent": Decimal(str(event["soc_percent"])),
                "battery_temperature_celsius": Decimal(str(event["battery_temperature_celsius"])) if event.get("battery_temperature_celsius") else None,
                "power_kw": Decimal(str(event["power_kw"])),
                "cumulative_energy_kwh": Decimal(str(event["cumulative_energy_kwh"])),
                "speed_kmh": Decimal(str(event.get("speed_kmh", "0.0"))),
                "odometer_km": Decimal(str(event["odometer_km"])),
                "latitude": Decimal(str(event["latitude"])) if event.get("latitude") else None,
                "longitude": Decimal(str(event["longitude"])) if event.get("longitude") else None,
            })

        accepted, ignored = TelemetryIngestionService.ingest_batch(parsed_events, org)
        return {
            "status": "success",
            "accepted": accepted,
            "ignored": ignored
        }
    except Exception as exc:
        logger.error("Error in process_telemetry_batch_async: %s", exc)
        if self.request.is_eager:
            # Re-raise in tests so pytest shows the exact traceback
            raise exc
        raise self.retry(exc=exc)