from decimal import Decimal
from rest_framework import serializers
from .models import TelemetryRecord


class TelemetryEventSerializer(serializers.ModelSerializer):
    vehicle_id = serializers.UUIDField(source="vehicle.id", read_only=True)

    class Meta:
        model = TelemetryRecord
        fields = [
            "id",
            "vehicle_id",
            "timestamp",
            "soc_percent",
            "battery_temperature_celsius",
            "power_kw",
            "cumulative_energy_kwh",
            "speed_kmh",
            "odometer_km",
            "latitude",
            "longitude",
            "ingested_at",
        ]
        read_only_fields = ["id", "ingested_at"]


class TelemetryIngestInputSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField(required=True)
    timestamp = serializers.DateTimeField(required=True)
    soc_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal("0.0"), max_value=Decimal("100.0"), required=True
    )
    battery_temperature_celsius = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    power_kw = serializers.DecimalField(max_digits=6, decimal_places=2, required=True)
    cumulative_energy_kwh = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal("0.0"), required=True
    )
    speed_kmh = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal("0.0"), required=False, default=Decimal("0.0")
    )
    odometer_km = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.0"), required=True
    )
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal("-90.0"), max_value=Decimal("90.0"), required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal("-180.0"), max_value=Decimal("180.0"), required=False, allow_null=True
    )


class TelemetryBatchIngestSerializer(serializers.Serializer):
    events = serializers.ListField(
        child=TelemetryIngestInputSerializer(),
        allow_empty=False,
        max_length=500,
        help_text="Batch of up to 500 telemetry events"
    )