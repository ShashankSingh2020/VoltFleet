import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import Organization, User
from apps.vehicles.models import Vehicle


class Anomaly(models.Model):
    class AnomalyType(models.TextChoices):
        HIGH_BATTERY_TEMP = "HIGH_BATTERY_TEMP", _("Abnormally High Battery Temperature")
        SUDDEN_SOC_DROP = "SUDDEN_SOC_DROP", _("Sudden Battery SOC Drop")
        HIGH_CONSUMPTION = "HIGH_CONSUMPTION", _("Excessive Energy Consumption Rate")
        STALE_TELEMETRY = "STALE_TELEMETRY", _("Stale Telemetry Gap")

    class Severity(models.TextChoices):
        LOW = "LOW", _("Low")
        MEDIUM = "MEDIUM", _("Medium")
        HIGH = "HIGH", _("High")
        CRITICAL = "CRITICAL", _("Critical")

    class Status(models.TextChoices):
        OPEN = "OPEN", _("Open / Unresolved")
        ACKNOWLEDGED = "ACKNOWLEDGED", _("Acknowledged")
        RESOLVED = "RESOLVED", _("Resolved")
        FALSE_POSITIVE = "FALSE_POSITIVE", _("False Positive")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="anomalies"
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="anomalies"
    )
    anomaly_type = models.CharField(max_length=40, choices=AnomalyType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    detected_at = models.DateTimeField(db_index=True)
    observed_value = models.CharField(max_length=100, help_text=_("Observed telemetry value, e.g. '52.4 °C'"))
    threshold_value = models.CharField(max_length=100, help_text=_("Threshold rule violated, e.g. '> 45.0 °C'"))
    evidence_summary = models.TextField(help_text=_("Deterministic evidence summary of the condition"))
    context_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "anomalies"
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["vehicle", "anomaly_type", "status"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.anomaly_type} on {self.vehicle.license_plate} ({self.status})"


class AnomalyResolutionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    anomaly = models.ForeignKey(
        Anomaly, on_delete=models.CASCADE, related_name="resolution_logs"
    )
    action_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="anomaly_resolutions"
    )
    action = models.CharField(max_length=30)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "anomaly_resolution_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.anomaly_id} by {self.action_by}"