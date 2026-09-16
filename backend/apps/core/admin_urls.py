"""
URL routing for admin endpoints.
"""

from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .admin_views import AdminUserViewSet, AdminStatsViewSet

app_name = 'admin'

router = SimpleRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'stats', AdminStatsViewSet, basename='admin-stats')

urlpatterns = [
    path('', include(router.urls)),
]
