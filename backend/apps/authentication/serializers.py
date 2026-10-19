from rest_framework import serializers
from django.db import transaction
from django.utils.text import slugify
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Organization, Membership


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "is_active", "created_at"]
        read_only_fields = ["id", "slug", "created_at"]


class MembershipSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source="organization.name")

    class Meta:
        model = Membership
        fields = ["id", "organization", "organization_name", "role", "is_active"]
        read_only_fields = ["id", "organization_name"]


class UserSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "memberships", "date_joined"]
        read_only_fields = ["id", "date_joined", "memberships"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    password_confirm = serializers.CharField(write_only=True, min_length=8, required=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    organization_name = serializers.CharField(max_length=255, required=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "A user with this email address already exists."})
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
            )

            org_name = validated_data["organization_name"]
            base_slug = slugify(org_name)
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            organization = Organization.objects.create(name=org_name, slug=slug)

            Membership.objects.create(
                user=user,
                organization=organization,
                role=Membership.RoleChoices.ORG_ADMIN,
                is_active=True,
            )

            return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        membership = user.memberships.filter(is_active=True).first()
        if membership:
            token["org_id"] = str(membership.organization.id)
            token["role"] = membership.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
        }
        active_membership = self.user.memberships.filter(is_active=True).first()
        if active_membership:
            data["organization"] = {
                "id": str(active_membership.organization.id),
                "name": active_membership.organization.name,
                "role": active_membership.role,
            }
        return data