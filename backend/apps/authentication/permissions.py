from rest_framework import permissions
from .models import Membership


class IsPlatformAdmin(permissions.BasePermission):
    """Permits access only to platform superadmins."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsOrgAdmin(permissions.BasePermission):
    """Permits access to Organization Admins or Platform Admins."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return request.user.memberships.filter(
            role=Membership.RoleChoices.ORG_ADMIN,
            is_active=True
        ).exists()


class IsFleetOperator(permissions.BasePermission):
    """Permits access to Fleet Operators, Org Admins, and Platform Admins."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        allowed_roles = [Membership.RoleChoices.ORG_ADMIN, Membership.RoleChoices.FLEET_OPERATOR]
        return request.user.memberships.filter(
            role__in=allowed_roles,
            is_active=True
        ).exists()