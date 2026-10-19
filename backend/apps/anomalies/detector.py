from decimal import Decimal
from datetime import timedelta
from typing import List, Dict, Any
from django.utils import timezone
from apps.vehicles.models import Vehicle
from apps.telemetry.models import TelemetryRecord
from .models import Anomaly


class AnomalyDetectionEngine:
    COOLDOWN_MINUTES = 60
    MAX_BATTERY_TEMP_CELSIUS = Decimal("45.0")
    MAX_SOC_DROP_PERCENT = Decimal("5.0")

    @classmethod
    def scan_organization(cls, organization) -> List[Anomaly]:
        """
        Scans all active vehicles in the organization and creates Anomaly records for detected violations.
        Returns list of newly created Anomaly instances.
        """
        vehicles = Vehicle.objects.filter(organization=organization, is_active=True).select_related("specification")
        newly_detected = []

        now = timezone.now()
        cooldown_window = now - timedelta(minutes=cls.COOLDOWN_MINUTES)

        for vehicle in vehicles:
            # Check 1: Stale telemetry gap
            last_record = TelemetryRecord.objects.filter(vehicle=vehicle).order_by("-timestamp").first()
            if last_record and (now - last_record.timestamp) > timedelta(minutes=120):
                if not cls._has_open_incident(vehicle, Anomaly.AnomalyType.STALE_TELEMETRY, cooldown_window):
                    anomaly = Anomaly.objects.create(
                        organization=organization,
                        vehicle=vehicle,
                        anomaly_type=Anomaly.AnomalyType.STALE_TELEMETRY,
                        severity=Anomaly.Severity.MEDIUM,
                        detected_at=now,
                        observed_value=f"{(now - last_record.timestamp).total_seconds() / 60:.0f} mins silent",
                        threshold_value="> 120 mins",
                        evidence_summary=f"No telemetry received since {last_record.timestamp.isoformat()}.",
                        context_data={"last_seen": last_record.timestamp.isoformat()}
                    )
                    newly_detected.append(anomaly)

            # Retrieve last 10 telemetry events to evaluate continuous physics
            recent_records = list(
                TelemetryRecord.objects.filter(vehicle=vehicle).order_by("-timestamp")[:10]
            )
            if not recent_records:
                continue

            # Check 2: High battery temperature on latest record
            latest = recent_records[0]
            if latest.battery_temperature_celsius and latest.battery_temperature_celsius > cls.MAX_BATTERY_TEMP_CELSIUS:
                if not cls._has_open_incident(vehicle, Anomaly.AnomalyType.HIGH_BATTERY_TEMP, cooldown_window):
                    anomaly = Anomaly.objects.create(
                        organization=organization,
                        vehicle=vehicle,
                        anomaly_type=Anomaly.AnomalyType.HIGH_BATTERY_TEMP,
                        severity=Anomaly.Severity.CRITICAL,
                        detected_at=latest.timestamp,
                        observed_value=f"{latest.battery_temperature_celsius} °C",
                        threshold_value=f"> {cls.MAX_BATTERY_TEMP_CELSIUS} °C",
                        evidence_summary=f"Battery core temperature reached {latest.battery_temperature_celsius} °C at {latest.timestamp.isoformat()}.",
                        context_data={"record_id": str(latest.id), "power_kw": str(latest.power_kw)}
                    )
                    newly_detected.append(anomaly)

            # Check 3: Sudden SOC drop between consecutive telemetry points
            if len(recent_records) >= 2:
                prev = recent_records[1]
                time_diff = (latest.timestamp - prev.timestamp).total_seconds() / 60.0
                if 0 < time_diff <= 10.0:
                    soc_drop = prev.soc_percent - latest.soc_percent
                    distance_diff = latest.odometer_km - prev.odometer_km
                    # SOC dropped > 5% in <= 10 min while travelling minimal distance (< 2 km)
                    if soc_drop > cls.MAX_SOC_DROP_PERCENT and distance_diff < Decimal("2.0"):
                        if not cls._has_open_incident(vehicle, Anomaly.AnomalyType.SUDDEN_SOC_DROP, cooldown_window):
                            anomaly = Anomaly.objects.create(
                                organization=organization,
                                vehicle=vehicle,
                                anomaly_type=Anomaly.AnomalyType.SUDDEN_SOC_DROP,
                                severity=Anomaly.Severity.HIGH,
                                detected_at=latest.timestamp,
                                observed_value=f"-{soc_drop}% in {time_diff:.1f} mins",
                                threshold_value=f"> {cls.MAX_SOC_DROP_PERCENT}% without proportional traction",
                                evidence_summary=f"SOC fell by {soc_drop}% across {distance_diff} km between {prev.timestamp.isoformat()} and {latest.timestamp.isoformat()}.",
                                context_data={
                                    "soc_before": str(prev.soc_percent),
                                    "soc_after": str(latest.soc_percent),
                                    "distance_delta_km": str(distance_diff)
                                }
                            )
                            newly_detected.append(anomaly)

        return newly_detected

    @classmethod
    def _has_open_incident(cls, vehicle, anomaly_type, cooldown_window) -> bool:
        """
        Suppresses duplicate alerts for an identical continuing condition within the cooldown window.
        """
        return Anomaly.objects.filter(
            vehicle=vehicle,
            anomaly_type=anomaly_type,
            status__in=[Anomaly.Status.OPEN, Anomaly.Status.ACKNOWLEDGED],
            detected_at__gte=cooldown_window
        ).exists()