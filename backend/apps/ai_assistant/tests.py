from decimal import Decimal
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import User, Organization, Membership
from apps.vehicles.models import Vehicle, VehicleSpecification
from apps.anomalies.models import Anomaly
from apps.optimizer.models import ChargingPlan


@pytest.mark.django_db
class TestAIAssistant:
    def setup_method(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="AI Guided Fleet", slug="ai-guided-fleet")
        self.user = User.objects.create_user(email="ai_operator@voltfleet.io", password="Password123!")
        Membership.objects.create(user=self.user, organization=self.org, role=Membership.RoleChoices.FLEET_OPERATOR)

        self.spec = VehicleSpecification.objects.create(
            make="VoltOmni",
            model="Prime",
            year=2025,
            usable_battery_capacity_kwh=Decimal("95.0"),
            max_ac_charging_power_kw=Decimal("22.0"),
            max_dc_charging_power_kw=Decimal("150.0"),
            efficiency_kwh_per_100km=Decimal("19.0"),
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.org,
            specification=self.spec,
            vin="1V9AIGENAI1234567",
            license_plate="EV-AI-01",
            current_soc_percent=Decimal("85.0"),
            odometer_km=Decimal("1200.0"),
        )
        self.chat_url = reverse("ai-fleet-chat")

    def test_grounded_fleet_chat_query(self):
        self.client.force_authenticate(user=self.user)
        payload = {"query": "How many vehicles are in our fleet and what is our status?"}

        response = self.client.post(self.chat_url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "answer" in response.data
        assert "MockAIProvider" in response.data["provider"]
        assert "1 active vehicles" in response.data["answer"]

    def test_anomaly_explanation_schema_validation(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        anomaly = Anomaly.objects.create(
            organization=self.org,
            vehicle=self.vehicle,
            anomaly_type=Anomaly.AnomalyType.HIGH_BATTERY_TEMP,
            severity=Anomaly.Severity.CRITICAL,
            detected_at=now,
            observed_value="53.0 °C",
            threshold_value="> 45.0 °C",
            evidence_summary="Extreme cell temperature detected under fast charging.",
        )

        explain_url = reverse("ai-anomaly-explain", kwargs={"anomaly_id": anomaly.id})
        response = self.client.get(explain_url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "summary" in data
        assert isinstance(data["hypotheses"], list)
        assert len(data["hypotheses"]) >= 1
        assert isinstance(data["recommended_actions"], list)
        assert 0.0 <= data["confidence_score"] <= 1.0

    def test_charging_plan_explanation(self):
        self.client.force_authenticate(user=self.user)
        now = timezone.now()

        plan = ChargingPlan.objects.create(
            organization=self.org,
            title="Overnight Smart Schedule",
            horizon_start=now,
            horizon_end=now + timezone.timedelta(hours=8),
            status=ChargingPlan.PlanStatus.ACTIVE,
            total_vehicles_scheduled=1,
            total_energy_kwh=Decimal("45.5"),
            total_estimated_cost=Decimal("6.82"),
        )

        explain_url = reverse("ai-plan-explain", kwargs={"plan_id": plan.id})
        response = self.client.get(explain_url)

        assert response.status_code == status.HTTP_200_OK
        assert "The optimization plan successfully scheduled 1 vehicles" in response.data["explanation"]