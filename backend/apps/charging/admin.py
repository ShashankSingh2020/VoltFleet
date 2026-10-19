from django.contrib import admin
from .models import ChargingStation, Charger, TariffPeriod, ChargingSession


@admin.register(ChargingStation)
class ChargingStationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "total_grid_capacity_kw", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "location_address")


@admin.register(Charger)
class ChargerAdmin(admin.ModelAdmin):
    list_display = ("identifier", "station", "power_type", "max_output_power_kw", "status")
    list_filter = ("power_type", "status", "station__organization")
    search_fields = ("identifier", "station__name")


@admin.register(TariffPeriod)
class TariffPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "start_time", "end_time", "cost_per_kwh", "is_active")
    list_filter = ("organization", "is_active")


@admin.register(ChargingSession)
class ChargingSessionAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "charger", "start_time", "end_time", "energy_delivered_kwh", "total_cost", "status")
    list_filter = ("status", "charger__station__organization")
    search_fields = ("vehicle__license_plate", "charger__identifier")