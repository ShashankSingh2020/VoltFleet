from decimal import Decimal
from rest_framework import serializers
from .models import Fleet, VehicleSpecification, Vehicle


class FleetSerializer(serializers.ModelSerializer):
    vehicle_count = serializers.IntegerField(source="vehicles.count", read_only=True)

    class Meta:
        model = Fleet
        fields = [
            "id",
            "organization",
            "name",
            "depot_location",
            "description",
            "vehicle_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class VehicleSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleSpecification
        fields = [
            "id",
            "make",
            "model",
            "year",
            "usable_battery_capacity_kwh",
            "max_ac_charging_power_kw",
            "max_dc_charging_power_kw",
            "efficiency_kwh_per_100km",
        ]


class VehicleSerializer(serializers.ModelSerializer):
    specification_detail = VehicleSpecificationSerializer(source="specification", read_only=True)
    fleet_name = serializers.ReadOnlyField(source="fleet.name")
    estimated_range_km = serializers.ReadOnlyField()

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "organization",
            "fleet",
            "fleet_name",
            "specification",
            "specification_detail",
            "vin",
            "license_plate",
            "nickname",
            "current_soc_percent",
            "odometer_km",
            "status",
            "target_departure_time",
            "target_departure_soc_percent",
            "estimated_range_km",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def validate_vin(self, value):
        cleaned_vin = value.strip().upper()
        if len(cleaned_vin) != 17 or not cleaned_vin.isalnum():
            raise serializers.ValidationError("VIN must be a valid 17-character alphanumeric string.")
        return cleaned_vin

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        active_membership = user.memberships.filter(is_active=True).first() if user else None
        user_org = active_membership.organization if active_membership else None

        # Ensure selected fleet belongs to the same organization
        fleet = attrs.get("fleet")
        if fleet and user_org and fleet.organization != user_org:
            raise serializers.ValidationError({"fleet": "Cannot assign vehicle to a fleet outside your organization."})

        # Ensure updated odometer cannot decrease
        if self.instance and "odometer_km" in attrs:
            new_odometer = attrs["odometer_km"]
            if new_odometer < self.instance.odometer_km:
                raise serializers.ValidationError(
                    {"odometer_km": f"Odometer reading cannot decrease below existing value ({self.instance.odometer_km} km)."}
                )

        return attrs