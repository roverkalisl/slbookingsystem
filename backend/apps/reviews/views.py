"""
Views for guest reviews.
"""

from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status

from .models import Review, ReviewResponse
from .serializers import ReviewSerializer, ReviewResponseSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for guest reviews.

    - GET /api/reviews/?property_id=<uuid> - public list of published reviews
    - POST /api/reviews/ - guest submits a review for their own, confirmed booking
    """

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Review.objects.filter(is_published=True).select_related('guest', 'response')

        property_id = self.request.query_params.get('property_id')
        if property_id:
            queryset = queryset.filter(property_id=property_id)

        return queryset.order_by('-created_at')

    def perform_update(self, serializer):
        review = self.get_object()
        if review.guest != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only edit your own review.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.guest != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only delete your own review.")
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            review = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'This booking has already been reviewed.'},
                status=status.HTTP_409_CONFLICT
            )
        return Response(
            {'success': True, 'data': ReviewSerializer(review, context={'request': request}).data},
            status=status.HTTP_201_CREATED
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ReviewResponseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for property-owner responses to reviews.

    - POST /api/reviews/{review_id}/response/ - owner responds to a review
    """

    serializer_class = ReviewResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReviewResponse.objects.filter(review_id=self.kwargs.get('review_pk'))

    def perform_create(self, serializer):
        # Missing review -> 404 (was an unhandled DoesNotExist / 500)
        review = get_object_or_404(Review, id=self.kwargs.get('review_pk'))

        if review.property.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only respond to reviews on your own properties.")

        if hasattr(review, 'response'):
            raise PermissionDenied("This review already has a response.")

        serializer.save(review=review, owner=self.request.user)
