"""
URL routing for authentication endpoints.
"""

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AuthViewSet

app_name = 'auth'

router = SimpleRouter()
router.register(r'', AuthViewSet, basename='auth')

urlpatterns = router.urls

