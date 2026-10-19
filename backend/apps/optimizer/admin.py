from django.contrib import admin
from .models import ChargingPlan, ChargingPlanItem


class ChargingPlanItemInline(admin.TabularInline):
    model = ChargingPlanItem
    extra = 0
    readonly_fields = ("vehicle", "charger", "scheduled_start", "scheduled_end", "energy_to_deliver_kwh", "estimated_cost", "is_feasible")


@admin.register(ChargingPlan)
class ChargingPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "status", "total_vehicles_scheduled", "total_energy_kwh", "total_estimated_cost", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("title",)
    inlines = [ChargingPlanItemInline]