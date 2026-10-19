from django.contrib import admin
from .models import TelemetryRecord


@admin.register(TelemetryRecord)
class TelemetryRecordAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "timestamp", "soc_percent", "power_kw", "speed_kmh", "battery_temperature_celsius")
    list_filter = ("vehicle__organization", "timestamp")
    search_fields = ("vehicle__license_plate", "vehicle__vin")
    readonly_fields = ("ingested_at",)