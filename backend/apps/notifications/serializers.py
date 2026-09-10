"""
Serializers for notification management.
"""

from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notification"""
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'channel', 'status', 'related_booking', 'created_at'
        ]
        read_only_fields = fields


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer for notification list"""
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'channel', 'status', 'created_at'
        ]
        read_only_fields = fields
