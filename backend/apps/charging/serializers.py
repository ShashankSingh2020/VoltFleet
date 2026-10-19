from decimal import Decimal
from rest_framework import serializers
from django.db.models import Q
from .models import ChargingStation, Charger, TariffPeriod, ChargingSession


class ChargerSerializer(serializers.ModelSerializer):
    station_name = serializers.ReadOnlyField(source="station.name")

    class Meta:
        model = Charger
        fields = [
            "id",
            "station",
            "station_name",
            "identifier",
            "power_type",
            "max_output_power_kw",
            "efficiency_factor",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ChargingStationSerializer(serializers.ModelSerializer):
    chargers = ChargerSerializer(many=True, read_only=True)
    total_chargers = serializers.IntegerField(source="chargers.count", read_only=True)

    class Meta:
        model = ChargingStation
        fields = [
            "id",
            "organization",
            "name",
            "location_address",
            "total_grid_capacity_kw",
            "is_active",
            "total_chargers",
            "chargers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class TariffPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffPeriod
        fields = [
            "id",
            "organization",
            "name",
            "start_time",
            "end_time",
            "cost_per_kwh",
            "is_active",
        ]
        read_only_fields = ["id", "organization"]


class ChargingSessionSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.ReadOnlyField(source="vehicle.license_plate")
    charger_identifier = serializers.ReadOnlyField(source="charger.identifier")

    class Meta:
        model = ChargingSession
        fields = [
            "id",
            "charger",
            "charger_identifier",
            "vehicle",
            "vehicle_plate",
            "start_time",
            "end_time",
            "initial_soc_percent",
            "final_soc_percent",
            "energy_delivered_kwh",
            "total_cost",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        membership = user.memberships.filter(is_active=True).first() if user else None
        user_org = membership.organization if membership else None

        charger = attrs.get("charger") or (self.instance.charger if self.instance else None)
        vehicle = attrs.get("vehicle") or (self.instance.vehicle if self.instance else None)
        start_time = attrs.get("start_time") or (self.instance.start_time if self.instance else None)
        end_time = attrs.get("end_time") or (self.instance.end_time if self.instance else None)

        # Cross-organization verification
        if charger and user_org and charger.station.organization != user_org:
            raise serializers.ValidationError({"charger": "Charger does not belong to your organization."})
        if vehicle and user_org and vehicle.organization != user_org:
            raise serializers.ValidationError({"vehicle": "Vehicle does not belong to your organization."})

        # Temporal sequence validation
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "Session end time must be strictly after start time."})

        # Physical SOC check
        init_soc = attrs.get("initial_soc_percent") or (self.instance.initial_soc_percent if self.instance else None)
        final_soc = attrs.get("final_soc_percent") or (self.instance.final_soc_percent if self.instance else None)
        if init_soc is not None and final_soc is not None and final_soc < init_soc:
            raise serializers.ValidationError(
                {"final_soc_percent": "Final SOC cannot be less than initial SOC during a charging session."}
            )

        # Charger conflict prevention (overlapping active sessions)
        session_status = attrs.get("status") or (self.instance.status if self.instance else ChargingSession.SessionStatus.IN_PROGRESS)
        if charger and start_time and session_status in [ChargingSession.SessionStatus.IN_PROGRESS, ChargingSession.SessionStatus.PLANNED]:
            conflict_query = ChargingSession.objects.filter(
                charger=charger,
                status__in=[ChargingSession.SessionStatus.IN_PROGRESS, ChargingSession.SessionStatus.PLANNED]
            )
            if self.instance:
                conflict_query = conflict_query.exclude(pk=self.instance.pk)

            # Check if an existing open session overlaps
            if end_time:
                conflict_query = conflict_query.filter(
                    Q(end_time__isnull=True, start_time__lte=end_time) |
                    Q(start_time__lt=end_time, end_time__gt=start_time)
                )
            else:
                conflict_query = conflict_query.filter(
                    Q(end_time__isnull=True) | Q(end_time__gt=start_time)
                )

            if conflict_query.exists():
                raise serializers.ValidationError(
                    {"charger": f"Charger {charger.identifier} has a conflicting active or planned session during this window."}
                )

        return attrs