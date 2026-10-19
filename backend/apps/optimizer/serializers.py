from rest_framework import serializers
from .models import ChargingPlan, ChargingPlanItem


class ChargingPlanItemSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.ReadOnlyField(source="vehicle.license_plate")
    charger_identifier = serializers.ReadOnlyField(source="charger.identifier")

    class Meta:
        model = ChargingPlanItem
        fields = [
            "id",
            "vehicle",
            "vehicle_plate",
            "charger",
            "charger_identifier",
            "scheduled_start",
            "scheduled_end",
            "energy_to_deliver_kwh",
            "estimated_cost",
            "target_soc_percent",
            "is_feasible",
            "notes",
            "created_at",
        ]


class ChargingPlanSerializer(serializers.ModelSerializer):
    items = ChargingPlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = ChargingPlan
        fields = [
            "id",
            "organization",
            "title",
            "horizon_start",
            "horizon_end",
            "status",
            "total_vehicles_scheduled",
            "total_energy_kwh",
            "total_estimated_cost",
            "algorithm_metadata",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "total_vehicles_scheduled",
            "total_energy_kwh",
            "total_estimated_cost",
            "algorithm_metadata",
            "created_at",
            "updated_at",
        ]


class OptimizeRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150, default="Smart Charging Optimization Run")
    horizon_start = serializers.DateTimeField(required=True)
    horizon_end = serializers.DateTimeField(required=True)
    vehicle_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    charger_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)

    def validate(self, attrs):
        if attrs["horizon_end"] <= attrs["horizon_start"]:
            raise serializers.ValidationError({"horizon_end": "horizon_end must be strictly after horizon_start."})
        return attrs