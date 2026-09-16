"""
Serializers for admin views.
"""

from rest_framework import serializers
from django.db.models import Count

from .models import User, Role


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users in admin panel"""

    roles = serializers.SerializerMethodField()
    property_count = serializers.SerializerMethodField()
    booking_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone',
            'is_active',
            'is_staff',
            'is_superuser',
            'roles',
            'property_count',
            'booking_count',
            'date_joined',
            'last_login',
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        """Get user roles"""
        return list(obj.roles.values_list('name', flat=True))

    def get_property_count(self, obj):
        """Count user's properties"""
        return obj.properties.count() if hasattr(obj, 'properties') else 0

    def get_booking_count(self, obj):
        """Count user's bookings (as guest)"""
        from apps.bookings.models import Booking
        return Booking.objects.filter(guest=obj).count()


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for admin user view"""

    roles = serializers.SerializerMethodField()
    properties = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone',
            'avatar_url',
            'bio',
            'is_active',
            'is_staff',
            'is_superuser',
            'email_verified',
            'phone_verified',
            'preferred_language',
            'notification_email',
            'notification_sms',
            'roles',
            'properties',
            'date_joined',
            'last_login',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        """Get user roles"""
        return list(obj.roles.values_list('name', flat=True))

    def get_properties(self, obj):
        """Get user's properties (for owners)"""
        from apps.properties.models import Property
        from apps.properties.serializers import PropertyListSerializer

        properties = Property.objects.filter(owner=obj)
        return PropertyListSerializer(properties, many=True).data


class AdminUserActivateDeactivateSerializer(serializers.Serializer):
    """Serializer for activate/deactivate action"""

    is_active = serializers.BooleanField()
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class AdminDashboardStatsSerializer(serializers.Serializer):
    """Serializer for admin dashboard statistics"""

    total_users = serializers.IntegerField()
    total_owners = serializers.IntegerField()
    total_guests = serializers.IntegerField()

    total_properties = serializers.IntegerField()
    pending_properties = serializers.IntegerField()
    approved_properties = serializers.IntegerField()
    rejected_properties = serializers.IntegerField()
    suspended_properties = serializers.IntegerField()

    total_bookings = serializers.IntegerField()
    pending_bookings = serializers.IntegerField()
    confirmed_bookings = serializers.IntegerField()
    completed_bookings = serializers.IntegerField()
    cancelled_bookings = serializers.IntegerField()

    platform_revenue = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        default=0
    )
