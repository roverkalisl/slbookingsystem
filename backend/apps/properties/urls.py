"""
URL routing for property endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PropertyTypeViewSet, AmenityViewSet, DestinationViewSet,
    PropertyViewSet, RoomTypeViewSet
)

app_name = 'properties'

router = DefaultRouter()
router.register(r'types', PropertyTypeViewSet, basename='property-type')
router.register(r'amenities', AmenityViewSet, basename='amenity')
router.register(r'destinations', DestinationViewSet, basename='destination')
router.register(r'', PropertyViewSet, basename='property')
router.register(r'rooms', RoomTypeViewSet, basename='room-type')

urlpatterns = [
    path('', include(router.urls)),
]
