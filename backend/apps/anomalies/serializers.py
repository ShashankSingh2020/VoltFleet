from rest_framework import serializers
from .models import Anomaly, AnomalyResolutionLog


class AnomalyResolutionLogSerializer(serializers.ModelSerializer):
    action_by_email = serializers.ReadOnlyField(source="action_by.email")

    class Meta:
        model = AnomalyResolutionLog
        fields = ["id", "action_by_email", "action", "notes", "created_at"]


class AnomalySerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.ReadOnlyField(source="vehicle.license_plate")
    resolution_logs = AnomalyResolutionLogSerializer(many=True, read_only=True)

    class Meta:
        model = Anomaly
        fields = [
            "id",
            "organization",
            "vehicle",
            "vehicle_plate",
            "anomaly_type",
            "severity",
            "status",
            "detected_at",
            "observed_value",
            "threshold_value",
            "evidence_summary",
            "context_data",
            "resolution_logs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "vehicle",
            "anomaly_type",
            "severity",
            "detected_at",
            "observed_value",
            "threshold_value",
            "evidence_summary",
            "context_data",
            "created_at",
            "updated_at",
        ]


class AnomalyActionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")