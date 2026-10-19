import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.vehicles.models import Vehicle


class TelemetryRecord(models.Model):
    """
    Time-indexed log of vehicle physical and electrical metrics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="telemetry_records"
    )
    timestamp = models.DateTimeField(db_index=True)

    # Battery & Electrical Dynamics
    soc_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.0")), MaxValueValidator(Decimal("100.0"))],
        help_text=_("Battery State of Charge (0-100%)")
    )
    battery_temperature_celsius = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Pack core temperature in °C")
    )
    power_kw = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text=_("Net power in kW: Positive = Charging into battery, Negative = Discharge / Traction")
    )
    cumulative_energy_kwh = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Cumulative lifetime energy consumption measured from onboard BMS")
    )

    # Kinematic & Spatial State
    speed_kmh = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Vehicle ground speed in km/h")
    )
    odometer_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text=_("Odometer distance in km at time of measurement")
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-90.0")), MaxValueValidator(Decimal("90.0"))]
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-180.0")), MaxValueValidator(Decimal("180.0"))]
    )

    # Ingestion Metadata
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "telemetry_records"
        ordering = ["-timestamp"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle", "timestamp"],
                name="unique_vehicle_telemetry_timestamp"
            )
        ]
        indexes = [
            models.Index(fields=["vehicle", "-timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.vehicle.license_plate} @ {self.timestamp} - SOC {self.soc_percent}%"