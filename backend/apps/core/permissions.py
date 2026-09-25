"""
Custom permission classes for SL Booking.
"""

from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Allow access only to admin users.

    Checks:
    - Django is_staff flag
    - Django is_superuser flag
    - Custom super_admin role
    """

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and (
                request.user.is_staff or
                request.user.is_superuser or
                request.user.has_role('super_admin')
            )
        )


class IsPropertyOwnerOrAdmin(permissions.BasePermission):
    """
    Allow only users with the property_owner role, or admins (same admin
    definition as IsAdminUser: is_staff, is_superuser or the super_admin
    role). Roles are read from the database - never from the request.
    """

    message = 'Only property owners can create properties.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and
            user.is_authenticated and (
                user.is_admin or
                user.has_role('property_owner')
            )
        )


class IsSuperAdmin(permissions.BasePermission):
    """
    Allow access only to Django superuser.
    More restrictive than IsAdminUser.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )
