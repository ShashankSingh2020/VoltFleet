import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import Organization
from apps.vehicles.models import Vehicle
from apps.charging.models import Charger


class ChargingPlan(models.Model):
    class PlanStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        ACTIVE = "ACTIVE", _("Active / Scheduled")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Infeasible / Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="charging_plans"
    )
    title = models.CharField(max_length=150, default="Optimization Run")
    horizon_start = models.DateTimeField()
    horizon_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=PlanStatus.choices, default=PlanStatus.DRAFT)
    total_vehicles_scheduled = models.PositiveIntegerField(default=0)
    total_energy_kwh = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))]
    )
    total_estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))]
    )
    algorithm_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "charging_plans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status}) - {self.total_vehicles_scheduled} vehicles"


class ChargingPlanItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        ChargingPlan, on_delete=models.CASCADE, related_name="items"
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="plan_allocations"
    )
    charger = models.ForeignKey(
        Charger, on_delete=models.CASCADE, related_name="plan_allocations"
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    energy_to_deliver_kwh = models.DecimalField(
        max_digits=8, decimal_places=3, validators=[MinValueValidator(Decimal("0.0"))]
    )
    estimated_cost = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.0"))]
    )
    target_soc_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_feasible = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "charging_plan_items"
        ordering = ["scheduled_start"]

    def __str__(self):
        return f"{self.vehicle.license_plate} @ {self.charger.identifier} ({self.scheduled_start} - {self.scheduled_end})"