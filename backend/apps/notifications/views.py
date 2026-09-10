"""
Views for notification management.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer, NotificationListSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for notifications (read-only for users).

    Endpoints:
    - GET /api/notifications/ - List my notifications
    - GET /api/notifications/{id}/ - Notification detail
    - POST /api/notifications/{id}/mark-as-read/ - Mark as read
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get notifications for current user"""
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')

    def get_serializer_class(self):
        """Choose serializer based on action"""
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark notification as read.

        POST /api/notifications/{id}/mark-as-read/
        """
        try:
            notification = Notification.objects.get(id=pk, recipient=request.user)

            notification.status = 'read'
            notification.save()

            return Response(
                {
                    'success': True,
                    'message': 'Notification marked as read',
                    'data': NotificationSerializer(notification).data
                },
                status=status.HTTP_200_OK
            )

        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Get unread notifications.

        GET /api/notifications/unread/
        """
        notifications = Notification.objects.filter(
            recipient=request.user,
            status__in=['pending', 'sent']
        ).order_by('-created_at')[:10]

        serializer = NotificationListSerializer(notifications, many=True)

        return Response(
            {
                'success': True,
                'count': notifications.count(),
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """
        Mark all notifications as read.

        POST /api/notifications/mark-all-as-read/
        """
        Notification.objects.filter(
            recipient=request.user,
            status__in=['pending', 'sent']
        ).update(status='read')

        return Response(
            {
                'success': True,
                'message': 'All notifications marked as read'
            },
            status=status.HTTP_200_OK
        )
