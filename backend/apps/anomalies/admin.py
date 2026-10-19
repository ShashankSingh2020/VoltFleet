from django.contrib import admin
from .models import Anomaly, AnomalyResolutionLog


class AnomalyResolutionLogInline(admin.TabularInline):
    model = AnomalyResolutionLog
    extra = 0
    readonly_fields = ("action_by", "action", "notes", "created_at")


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ("anomaly_type", "vehicle", "severity", "status", "detected_at", "observed_value")
    list_filter = ("severity", "status", "anomaly_type", "organization")
    search_fields = ("vehicle__license_plate", "evidence_summary")
    readonly_fields = ("detected_at", "created_at", "updated_at")
    inlines = [AnomalyResolutionLogInline]