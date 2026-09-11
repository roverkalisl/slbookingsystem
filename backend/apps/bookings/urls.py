from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import BookingViewSet

app_name = 'bookings'

router = SimpleRouter()
router.register(r'', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
]
