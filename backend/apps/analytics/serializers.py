from rest_framework import serializers


class FleetSummaryResponseSerializer(serializers.Serializer):
    total_vehicles = serializers.IntegerField()
    status_breakdown = serializers.DictField(child=serializers.IntegerField())
    total_distance_km = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_energy_kwh = serializers.DecimalField(max_digits=14, decimal_places=3)
    average_efficiency_kwh_per_100km = serializers.DecimalField(
        max_digits=6, decimal_places=2, allow_null=True
    )
    average_soc_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )


class VehicleEfficiencyResponseSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField()
    license_plate = serializers.CharField()
    distance_km = serializers.DecimalField(max_digits=10, decimal_places=2)
    energy_consumed_kwh = serializers.DecimalField(max_digits=12, decimal_places=3)
    realized_efficiency_kwh_per_100km = serializers.DecimalField(
        max_digits=6, decimal_places=2, allow_null=True
    )
    average_soc_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    average_battery_temp_celsius = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    data_points_analyzed = serializers.IntegerField()