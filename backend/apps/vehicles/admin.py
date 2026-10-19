from django.contrib import admin
from .models import Fleet, VehicleSpecification, Vehicle


@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "depot_location", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "depot_location")


@admin.register(VehicleSpecification)
class VehicleSpecificationAdmin(admin.ModelAdmin):
    list_display = ("make", "model", "year", "usable_battery_capacity_kwh", "max_dc_charging_power_kw")
    list_filter = ("make", "year")
    search_fields = ("make", "model")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("license_plate", "organization", "fleet", "specification", "current_soc_percent", "status")
    list_filter = ("organization", "status", "fleet")
    search_fields = ("license_plate", "vin", "nickname")
    readonly_fields = ("estimated_range_km",)