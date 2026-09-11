"""
URL routing for property endpoints.
"""

from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import (
    PropertyTypeViewSet, AmenityViewSet, DestinationViewSet,
    PropertyViewSet, RoomTypeViewSet, SearchViewSet, DestinationViewSetDetail
)

app_name = 'properties'

router = SimpleRouter()
router.register(r'types', PropertyTypeViewSet, basename='property-type')
router.register(r'amenities', AmenityViewSet, basename='amenity')
router.register(r'destinations', DestinationViewSet, basename='destination')
router.register(r'search', SearchViewSet, basename='search')
router.register(r'', PropertyViewSet, basename='property')
router.register(r'rooms', RoomTypeViewSet, basename='room-type')

urlpatterns = [
    path('', include(router.urls)),
    # Destination detail with slug
    path('destinations/<slug:slug>/', DestinationViewSetDetail.as_view({'get': 'retrieve'}), name='destination-detail'),
]
