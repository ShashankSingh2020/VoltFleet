from django.contrib import admin
from .models import User, Organization, Membership, AuditLog


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("is_staff", "is_active")
    ordering = ("email",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("user__email", "organization__name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "resource_type", "resource_id", "ip_address")
    list_filter = ("action", "resource_type")
    search_fields = ("actor__email", "action", "resource_id")
    readonly_fields = ("created_at",)