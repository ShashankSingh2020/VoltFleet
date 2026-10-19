from rest_framework import serializers
from .models import TelemetryRecord


class TelemetryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelemetryRecord
        fields = [
            "id",
            "vehicle",
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


class TelemetryIngestBatchSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField(required=True)
    timestamp = serializers.DateTimeField(required=True)
    soc_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=True)
    battery_temperature_celsius = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    power_kw = serializers.DecimalField(
        max_digits=7, decimal_places=2, required=False, allow_null=True, default=0.0
    )
    cumulative_energy_kwh = serializers.DecimalField(
        max_digits=10, decimal_places=3, required=False, allow_null=True, default=0.0
    )
    speed_kmh = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True, default=0.0
    )
    odometer_km = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True, default=0.0
    )
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
