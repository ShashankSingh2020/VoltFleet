import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import User, Organization, Membership


@pytest.mark.django_db
class TestAuthenticationAPI:
    def setup_method(self):
        self.client = APIClient()
        self.register_url = reverse("auth-register")
        self.login_url = reverse("token_obtain_pair")
        self.profile_url = reverse("user-profile")

    def test_user_registration_creates_org_and_admin_role(self):
        payload = {
            "email": "operator@voltfleet.io",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "first_name": "Fleet",
            "last_name": "Manager",
            "organization_name": "Apex Logistics"
        }
        response = self.client.post(self.register_url, payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "operator@voltfleet.io"

        user = User.objects.get(email="operator@voltfleet.io")
        org = Organization.objects.get(name="Apex Logistics")
        membership = Membership.objects.get(user=user, organization=org)

        assert membership.role == Membership.RoleChoices.ORG_ADMIN

    def test_login_returns_jwt_with_org_claims(self):
        # Register user
        reg_payload = {
            "email": "driver@voltfleet.io",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "organization_name": "Volt Couriers"
        }
        self.client.post(self.register_url, reg_payload)

        # Login
        login_payload = {
            "email": "driver@voltfleet.io",
            "password": "SecurePassword123!"
        }
        response = self.client.post(self.login_url, login_payload)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["organization"]["name"] == "Volt Couriers"

    def test_protected_profile_endpoint_requires_auth(self):
        response = self.client.get(self.profile_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED