"""
URL routing for authentication endpoints.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AuthViewSet

app_name = 'auth'

router = DefaultRouter()
router.register(r'', AuthViewSet, basename='auth')

urlpatterns = router.urls
