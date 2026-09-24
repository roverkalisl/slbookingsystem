from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import ReviewViewSet, ReviewResponseViewSet

app_name = 'reviews'

router = SimpleRouter()
router.register(r'', ReviewViewSet, basename='review')

urlpatterns = [
    path('<uuid:review_pk>/response/', ReviewResponseViewSet.as_view({'post': 'create'}), name='review-response'),
    path('', include(router.urls)),
]
