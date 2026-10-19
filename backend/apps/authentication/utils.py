from typing import Optional
from django.contrib.auth import get_user_model
from apps.authentication.models import Membership, Organization

User = get_user_model()


def get_active_user_organization(user: User) -> Optional[Organization]:
    """
    Deterministically resolves a user's active organization via active Membership.
    Prioritizes active memberships, falling back to any organization membership
    if is_active field is absent on the Membership model.
    """
    if not user or not user.is_authenticated:
        return None

    membership_qs = Membership.objects.select_related("organization").filter(user=user)
    
    # Check if Membership model defines an is_active field
    if hasattr(Membership, "is_active"):
        active_mem = membership_qs.filter(is_active=True).first()
        if active_mem:
            return active_mem.organization

    # Standard fallback to first membership
    first_mem = membership_qs.first()
    if first_mem:
        return first_mem.organization

    # Superuser fallback or direct attribute if set
    if hasattr(user, "organization") and user.organization:
        return user.organization

    return None
