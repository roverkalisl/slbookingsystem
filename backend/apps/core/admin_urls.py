"""
URL routing for admin endpoints.
"""

from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .admin_views import AdminUserViewSet, AdminStatsViewSet
from .admin_booking_views import (
    AdminBookingViewSet,
    AdminPaymentViewSet,
    AdminRefundViewSet,
)

app_name = 'admin'

router = SimpleRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'stats', AdminStatsViewSet, basename='admin-stats')
router.register(r'bookings', AdminBookingViewSet, basename='admin-bookings')
router.register(r'payments', AdminPaymentViewSet, basename='admin-payments')
router.register(r'refunds', AdminRefundViewSet, basename='admin-refunds')

urlpatterns = [
    path('', include(router.urls)),
]
