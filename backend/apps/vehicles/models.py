import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import Organization


class Fleet(models.Model):
    """
    Logical grouping of vehicles stationed at a particular depot or operation zone.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="fleets"
    )
    name = models.CharField(max_length=150)
    depot_location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fleets"
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class VehicleSpecification(models.Model):
    """
    Standard OEM vehicle specifications describing battery capacity and charging profiles.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    usable_battery_capacity_kwh = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("5.0"))],
        help_text=_("Total usable battery energy in kilowatt-hours (kWh)")
    )
    max_ac_charging_power_kw = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("11.0"),
        validators=[MinValueValidator(Decimal("1.0"))],
        help_text=_("Maximum onboard AC charger limit in kW")
    )
    max_dc_charging_power_kw = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("150.0"),
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Maximum DC fast-charging limit in kW")
    )
    efficiency_kwh_per_100km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("18.0"),
        validators=[MinValueValidator(Decimal("1.0"))],
        help_text=_("Manufacturer rated energy efficiency (kWh/100km)")
    )

    class Meta:
        db_table = "vehicle_specifications"
        unique_together = ("make", "model", "year")
        ordering = ["make", "model", "year"]

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.usable_battery_capacity_kwh} kWh)"


class Vehicle(models.Model):
    """
    Physical Electric Vehicle instance monitored by the platform.
    """
    class StatusChoices(models.TextChoices):
        AVAILABLE = "AVAILABLE", _("Available for dispatch")
        IN_TRANSIT = "IN_TRANSIT", _("On route / in transit")
        CHARGING = "CHARGING", _("Connected to charger")
        MAINTENANCE = "MAINTENANCE", _("In maintenance")
        OUT_OF_SERVICE = "OUT_OF_SERVICE", _("Out of service / Decommissioned")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="vehicles"
    )
    fleet = models.ForeignKey(
        Fleet, on_delete=models.SET_NULL, null=True, blank=True, related_name="vehicles"
    )
    specification = models.ForeignKey(
        VehicleSpecification, on_delete=models.PROTECT, related_name="vehicles"
    )
    vin = models.CharField(max_length=17, unique=True, help_text=_("Vehicle Identification Number"))
    license_plate = models.CharField(max_length=30)
    nickname = models.CharField(max_length=100, blank=True)

    # Telemetric baselines and live state
    current_soc_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.0"),
        validators=[
            MinValueValidator(Decimal("0.0")),
            MaxValueValidator(Decimal("100.0"))
        ],
        help_text=_("Current Battery State of Charge (0.00% to 100.00%)")
    )
    odometer_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Current cumulative odometer reading in kilometers")
    )
    status = models.CharField(
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.AVAILABLE
    )

    # Operational requirements for smart charging optimization
    target_departure_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Next scheduled operational departure time")
    )
    target_departure_soc_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("90.0"),
        validators=[
            MinValueValidator(Decimal("10.0")),
            MaxValueValidator(Decimal("100.0"))
        ],
        help_text=_("Minimum acceptable SOC required upon target departure")
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vehicles"
        ordering = ["license_plate"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "target_departure_time"]),
        ]

    def __str__(self):
        return f"{self.license_plate} - {self.specification.make} {self.specification.model} ({self.status})"

    @property
    def estimated_range_km(self) -> Decimal:
        """
        Estimates remaining driving range based on current SOC and rated efficiency.
        Range (km) = (Battery kWh * (SOC / 100)) / (Efficiency kWh/100km / 100)
        """
        nominal_kwh = self.specification.usable_battery_capacity_kwh
        efficiency = self.specification.efficiency_kwh_per_100km
        current_kwh = nominal_kwh * (self.current_soc_percent / Decimal("100.0"))
        if efficiency > Decimal("0.0"):
            return round((current_kwh / efficiency) * Decimal("100.0"), 1)
        return Decimal("0.0")