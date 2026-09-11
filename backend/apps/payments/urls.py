from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import PaymentViewSet, PaymentWebhookViewSet

app_name = 'payments'

router = SimpleRouter()
router.register(r'', PaymentViewSet, basename='payment')
router.register(r'webhook', PaymentWebhookViewSet, basename='webhook')

urlpatterns = [
    path('', include(router.urls)),
]
