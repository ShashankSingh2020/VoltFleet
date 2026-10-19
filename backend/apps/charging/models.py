import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import Organization
from apps.vehicles.models import Vehicle


class ChargingStation(models.Model):
    """
    Physical charging depot or facility belonging to an Organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="charging_stations"
    )
    name = models.CharField(max_length=150)
    location_address = models.CharField(max_length=255, blank=True)
    total_grid_capacity_kw = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("10.0"))],
        help_text=_("Total peak electrical service capacity for this site in kW")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "charging_stations"
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.total_grid_capacity_kw} kW)"


class Charger(models.Model):
    """
    Individual charging point / EVSE (Electric Vehicle Supply Equipment).
    """
    class PowerType(models.TextChoices):
        AC_LEVEL_2 = "AC_LEVEL_2", _("AC Level 2")
        DC_FAST = "DC_FAST", _("DC Fast Charger")

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", _("Available")
        OCCUPIED = "OCCUPIED", _("Occupied / In Session")
        FAULTED = "FAULTED", _("Faulted")
        OFFLINE = "OFFLINE", _("Offline")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(
        ChargingStation, on_delete=models.CASCADE, related_name="chargers"
    )
    identifier = models.CharField(max_length=50, help_text=_("Port / Dispenser ID, e.g., CP-01"))
    power_type = models.CharField(max_length=20, choices=PowerType.choices, default=PowerType.DC_FAST)
    max_output_power_kw = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("3.0"))],
        help_text=_("Nameplate maximum power deliverable in kW")
    )
    efficiency_factor = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.92"),
        validators=[MinValueValidator(Decimal("0.50")), MaxValueValidator(Decimal("1.00"))],
        help_text=_("AC-to-DC conversion efficiency factor (e.g., 0.92 = 92%)")
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chargers"
        unique_together = ("station", "identifier")
        ordering = ["station", "identifier"]

    def __str__(self):
        return f"{self.station.name} - {self.identifier} ({self.max_output_power_kw} kW)"


class TariffPeriod(models.Model):
    """
    Time-of-Use (TOU) electricity pricing windows.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="tariff_periods"
    )
    name = models.CharField(max_length=100, help_text=_("e.g. Off-Peak Night, Peak Afternoon"))
    start_time = models.TimeField(help_text=_("Start time of rate period (HH:MM:SS)"))
    end_time = models.TimeField(help_text=_("End time of rate period (HH:MM:SS)"))
    cost_per_kwh = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text=_("Cost in currency units per kilowatt-hour (kWh)")
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tariff_periods"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.name} ({self.start_time}-{self.end_time}): /kWh"


class ChargingSession(models.Model):
    """
    A discrete vehicle charging event at a specific charger.
    """
    class SessionStatus(models.TextChoices):
        PLANNED = "PLANNED", _("Planned / Reserved")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    charger = models.ForeignKey(
        Charger, on_delete=models.PROTECT, related_name="sessions"
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name="charging_sessions"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    initial_soc_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.0")), MaxValueValidator(Decimal("100.0"))]
    )
    final_soc_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.0")), MaxValueValidator(Decimal("100.0"))]
    )
    energy_delivered_kwh = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Total electrical energy supplied to the battery pack in kWh")
    )
    total_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Calculated or billed electricity cost for this session")
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.IN_PROGRESS
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "charging_sessions"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["charger", "start_time", "end_time"]),
            models.Index(fields=["vehicle", "start_time"]),
        ]

    def __str__(self):
        return f"{self.vehicle.license_plate} @ {self.charger} ({self.status})"