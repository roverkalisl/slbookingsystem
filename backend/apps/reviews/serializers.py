"""
Serializers for guest reviews.
"""

from rest_framework import serializers
from apps.bookings.models import Booking
from .models import Review, ReviewResponse


class ReviewResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewResponse
        fields = ['id', 'response_text', 'created_at']
        read_only_fields = ['id', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for listing/creating reviews.

    Accepts the frontend's {booking_id, rating, title, comment} shape:
    - booking_id -> booking (write-only; the property is derived from the
      booking server-side, never trusted from the client)
    - rating -> overall_rating
    - title has no dedicated column on Review; it's folded into the stored
      comment rather than adding a new field for a single extra label.
    """

    booking_id = serializers.PrimaryKeyRelatedField(
        queryset=Booking.objects.all(), source='booking', write_only=True
    )
    rating = serializers.IntegerField(source='overall_rating', min_value=1, max_value=5, write_only=True)
    title = serializers.CharField(required=False, allow_blank=True, write_only=True)
    guest_name = serializers.SerializerMethodField()
    response = ReviewResponseSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'booking_id', 'property', 'guest', 'guest_name',
            'rating', 'title', 'overall_rating', 'cleanliness_rating',
            'location_rating', 'facilities_rating', 'service_rating',
            'value_rating', 'comment', 'created_at', 'response',
        ]
        read_only_fields = ['id', 'property', 'guest', 'overall_rating', 'created_at']

    def get_guest_name(self, obj):
        return obj.guest.get_full_name() or obj.guest.email

    def validate(self, attrs):
        booking = attrs.get('booking')
        request = self.context.get('request')

        if booking is not None and request is not None:
            if booking.guest != request.user:
                raise serializers.ValidationError({'booking_id': 'You can only review your own bookings.'})

            if booking.status not in ('confirmed', 'completed'):
                raise serializers.ValidationError(
                    {'booking_id': 'You can only review a booking that has been confirmed by the property.'}
                )

            if hasattr(booking, 'review'):
                raise serializers.ValidationError({'booking_id': 'This booking has already been reviewed.'})

        return attrs

    def create(self, validated_data):
        title = validated_data.pop('title', '')
        booking = validated_data['booking']
        comment = validated_data.get('comment', '') or ''
        if title:
            comment = f"{title}\n\n{comment}".strip()

        return Review.objects.create(
            booking=booking,
            property=booking.property,
            guest=booking.guest,
            comment=comment,
            overall_rating=validated_data['overall_rating'],
            cleanliness_rating=validated_data.get('cleanliness_rating'),
            location_rating=validated_data.get('location_rating'),
            facilities_rating=validated_data.get('facilities_rating'),
            service_rating=validated_data.get('service_rating'),
            value_rating=validated_data.get('value_rating'),
        )
