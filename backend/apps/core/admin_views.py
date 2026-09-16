"""
Admin views for user management and dashboard statistics.
"""

from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import User
from .permissions import IsAdminUser
from .admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserActivateDeactivateSerializer,
    AdminDashboardStatsSerializer,
)
from apps.properties.models import Property
from apps.bookings.models import Booking
from apps.payments.models import Payment


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin user management ViewSet.

    Endpoints:
    - GET /api/admin/users/ - List users
    - GET /api/admin/users/{id}/ - User details
    - POST /api/admin/users/{id}/activate/ - Activate user
    - POST /api/admin/users/{id}/deactivate/ - Deactivate user
    """

    permission_classes = [IsAdminUser]
    queryset = User.objects.all().prefetch_related('roles')
    serializer_class = AdminUserListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_staff']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone']
    ordering_fields = ['date_joined', 'email', 'first_name', 'last_login']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        """Choose serializer based on action"""
        if self.action == 'retrieve':
            return AdminUserDetailSerializer
        elif self.action in ['activate', 'deactivate']:
            return AdminUserActivateDeactivateSerializer
        return AdminUserListSerializer

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate a user.

        POST /api/admin/users/{id}/activate/
        """
        user = self.get_object()

        if user.id == request.user.id:
            return Response(
                {'error': 'Cannot activate/deactivate yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = True
        user.save()

        return Response(
            {
                'success': True,
                'message': f'User {user.email} activated',
                'data': AdminUserDetailSerializer(user).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate a user.

        POST /api/admin/users/{id}/deactivate/
        {
            "reason": "Optional reason for deactivation"
        }
        """
        user = self.get_object()

        if user.id == request.user.id:
            return Response(
                {'error': 'Cannot activate/deactivate yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.save()

        return Response(
            {
                'success': True,
                'message': f'User {user.email} deactivated',
                'data': AdminUserDetailSerializer(user).data
            },
            status=status.HTTP_200_OK
        )


class AdminStatsViewSet(viewsets.ViewSet):
    """
    Admin dashboard statistics ViewSet.

    Endpoints:
    - GET /api/admin/stats/ - Dashboard statistics
    """

    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get dashboard statistics.

        GET /api/admin/stats/dashboard/
        """
        # Calculate user statistics
        total_users = User.objects.count()
        total_owners = User.objects.filter(roles__name='property_owner').distinct().count()
        total_guests = User.objects.filter(roles__name='guest').distinct().count()

        # Calculate property statistics
        total_properties = Property.objects.count()
        pending_properties = Property.objects.filter(status='pending_approval').count()
        approved_properties = Property.objects.filter(status='approved').count()
        rejected_properties = Property.objects.filter(status='rejected').count()
        suspended_properties = Property.objects.filter(status='suspended').count()

        # Calculate booking statistics
        total_bookings = Booking.objects.count()
        pending_bookings = Booking.objects.filter(status='pending').count()
        confirmed_bookings = Booking.objects.filter(status='confirmed').count()
        completed_bookings = Booking.objects.filter(status='completed').count()
        cancelled_bookings = Booking.objects.filter(status='cancelled').count()

        # Calculate revenue (sum of paid/completed payments)
        platform_revenue = Decimal('0')
        try:
            paid_payments = Payment.objects.filter(status='paid')
            for payment in paid_payments:
                platform_revenue += payment.amount
        except Exception:
            platform_revenue = None

        # Calculate average rating
        average_rating = Decimal('0')
        try:
            properties_with_rating = Property.objects.exclude(average_rating=0)
            if properties_with_rating.exists():
                total_rating = sum(p.average_rating for p in properties_with_rating)
                average_rating = Decimal(str(total_rating / properties_with_rating.count()))
        except Exception:
            average_rating = Decimal('0')

        stats = {
            'total_users': total_users,
            'total_owners': total_owners,
            'total_guests': total_guests,
            'total_properties': total_properties,
            'pending_properties': pending_properties,
            'approved_properties': approved_properties,
            'rejected_properties': rejected_properties,
            'suspended_properties': suspended_properties,
            'total_bookings': total_bookings,
            'pending_bookings': pending_bookings,
            'confirmed_bookings': confirmed_bookings,
            'completed_bookings': completed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'platform_revenue': platform_revenue,
            'average_rating': average_rating,
        }

        serializer = AdminDashboardStatsSerializer(stats)
        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
