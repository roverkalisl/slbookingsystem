"""Review models"""

import uuid
from django.db import models
from apps.bookings.models import Booking
from apps.properties.models import Property
from apps.core.models import User


class Review(models.Model):
    """Guest reviews"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, unique=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    guest = models.ForeignKey(User, on_delete=models.CASCADE)

    # Ratings
    overall_rating = models.IntegerField()
    cleanliness_rating = models.IntegerField(blank=True, null=True)
    location_rating = models.IntegerField(blank=True, null=True)
    facilities_rating = models.IntegerField(blank=True, null=True)
    service_rating = models.IntegerField(blank=True, null=True)
    value_rating = models.IntegerField(blank=True, null=True)

    comment = models.TextField(blank=True, null=True)

    is_verified = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        indexes = [
            models.Index(fields=['property_id']),
            models.Index(fields=['guest_id']),
            models.Index(fields=['overall_rating']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return f"Review by {self.guest.email} for {self.property.name}"


class ReviewResponse(models.Model):
    """Owner response to review"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.OneToOneField(Review, on_delete=models.CASCADE, unique=True, related_name='response')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    response_text = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'review_responses'

    def __str__(self):
        return f"Response to review {self.review.id}"
