from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, PaymentWebhookViewSet

app_name = 'payments'

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')
router.register(r'webhook', PaymentWebhookViewSet, basename='webhook')

urlpatterns = [
    path('', include(router.urls)),
]
